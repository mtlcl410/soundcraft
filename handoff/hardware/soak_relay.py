"""Drive both real DIN legs and a separately measured transient Windows MIDI relay."""
import contextlib,csv,json,os,queue,sys,threading,time
from pathlib import Path
import psutil
from manual_run import hw,cmd,desktop,save,live_midi
from desktop_sync import rpc
from virtual_pair import pair
from wire_source import sleep_until
from m1 import np

def soak(f,secs):
    with contextlib.ExitStack() as stack:
        left,right=stack.enter_context(pair(f))
        time.sleep(1.5)
        port=stack.enter_context(desktop(f,None))
        # Source leg UM OUT -> Model 12 IN; sink leg Model 12 OUT -> UM IN.
        tx,physical,_=stack.enter_context(live_midi(tx_name='UM-ONE',rx_name='Model 12 MIDI'))
        relay,seen,ports=stack.enter_context(live_midi(tx_name=left,rx_name=right))
        _,returned,names=stack.enter_context(live_midi(rx_name='UM-ONE'))
        save(f/'ports.json',dict(virtual=ports,returned=names))
        save(f/'follow.json',cmd(port,'setup.midi_clock_follow',input=right,enabled=True,loss_policy='coast'))
        save(f/'clock.json',cmd(port,'setup.midi_beat_clock',enabled=True,ports={'Model 12 MIDI':dict(enabled=True,offset_samples=0)}))
        save(f/'mtc-out.json',rpc(port,'engine.execute',dict(command='setup.mtc_output',params=dict(enabled=True,port='Model 12 MIDI',offset_samples=0))))
        if 'SC_AUDIT_BEAT_COMPENSATION' in os.environ:
            value = os.environ['SC_AUDIT_BEAT_COMPENSATION']=='on'
            cmd(port,'setup.midi_beat_clock',compensation=dict(beat_clock=value,mtc=True,notes=False))
            status = cmd(port,'setup.midi_sync_status')
            save(f/'compensation-verified.json',status)
            if status['settings']['compensation']['beat_clock'] != value:
                raise RuntimeError('Requested per-protocol setting was not applied')
        time.sleep(.8)
        while not returned.empty():returned.get_nowait()
        quit=threading.Event();err=[]
        def pump():
            try:
                with (f/'relay.csv').open('x',newline='') as log:
                    w=csv.writer(log);w.writerow(['arrival_ns','entry_ns','return_ns','hex'])
                    while not quit.is_set() or not physical.empty():
                        try:t,m,_=physical.get(timeout=.05)
                        except queue.Empty:continue
                        if m not in ((250,),(248,),(252,)):continue
                        entry=time.perf_counter_ns();relay.send_message(list(m));w.writerow([t,entry,time.perf_counter_ns(),bytes(m).hex()])
            except Exception as ex:err.append(repr(ex));quit.set()
        def log_port(pathname,inbox):
            try:
                with (f/pathname).open('x',newline='') as log:
                    w=csv.writer(log);w.writerow(['at_ns','hex'])
                    while not quit.is_set() or not inbox.empty():
                        try:t,m,_=inbox.get(timeout=.05)
                        except queue.Empty:continue
                        if m!=(254,):w.writerow([t,bytes(m).hex()])
            except Exception as ex:err.append(repr(ex));quit.set()
        def state():
            try:
                proc=psutil.Process(json.loads((f/'control.json').read_text())['pid'])
                with (f/'state.jsonl').open('x',buffering=1) as log:
                    while not quit.is_set():
                        t=time.perf_counter_ns();s=cmd(port,'setup.midi_sync_status')
                        print(json.dumps(dict(at_ns=t,s=s,rss=proc.memory_info().rss,private_bytes=proc.memory_info().private,relay_q=physical.qsize(),drain_q=returned.qsize())),file=log)
                        quit.wait(1)
            except Exception as ex:err.append(repr(ex));quit.set()
        threads=[threading.Thread(target=fn,args=a) for fn,a in [(pump,()),(log_port,('ingress.csv',seen)),(log_port,('egress.csv',returned)),(state,())]]
        for thread in threads:thread.start()
        try:
            origin=time.perf_counter_ns()+500_000_000
            with (f/'source.csv').open('x',newline='') as log:
                w=csv.writer(log);w.writerow(['due_ns','send_ns','hex'])
                sleep_until(origin);tx.send_message([250])
                for i in range(secs*48):
                    if err:raise RuntimeError(err)
                    deadline=origin+round(i*1e9/48);sleep_until(deadline)
                    t=time.perf_counter_ns();tx.send_message([248]);w.writerow([deadline,t,'f8'])
                sleep_until(origin+secs*1_000_000_000)
        finally:
            tx.send_message([252]);time.sleep(.6);quit.set()
            for thread in threads:thread.join(9)
        if err:raise RuntimeError(err)
        save(f/'after.json',cmd(port,'setup.midi_sync_status'))
        cmd(port,'setup.midi_clock_follow',enabled=False)
        cmd(port,'setup.mtc_output',enabled=False)
        cmd(port,'setup.midi_beat_clock',enabled=False)
    return analyse(f,secs)

def times(f,name,typ,key):
    with (f/name).open() as fp:
        return np.fromiter((int(row[key]) for row in csv.DictReader(fp) if row['hex'].startswith(typ)),dtype=np.int64)
def analyse(f,secs):
    original=times(f,'source.csv','f8','send_ns');wire=times(f,'relay.csv','f8','arrival_ns')
    entry=times(f,'relay.csv','f8','entry_ns');ingress=times(f,'ingress.csv','f8','at_ns');out=times(f,'egress.csv','f8','at_ns');qf=times(f,'egress.csv','f1','at_ns')
    states=[json.loads(l) for l in (f/'state.jsonl').read_text().splitlines()]
    result=dict(seconds=secs,expected_clock=secs*48,source=len(original),physical_input=len(wire),relayed_input=len(ingress),received_clock=len(out),expected_qf=secs*120,received_qf=len(qf),status=states[-1]['s'])
    def describe(x):return dict(median=float(np.median(x)),p99=float(np.percentile(x,99)),maximum=float(max(x)))
    if len(original)==len(wire)==len(entry)==len(ingress):
        result.update(din_in_ms=describe((wire-original)/1e6),relay_dispatch_ms=describe((entry-wire)/1e6),virtual_ms=describe((ingress-entry)/1e6),added_ms=describe((ingress-wire)/1e6))
    with (f/'egress.csv').open() as stream:
        last=None;bad=0;commands=[]
        for row in csv.DictReader(stream):
            m=bytes.fromhex(row['hex'])
            if m[0]==241:
                piece=m[1]>>4;bad+=last is not None and piece!=(last+1)%8;last=piece
            elif m[0] not in (248,254):commands.append(row)
    result.update(discontinuous_qf_pieces=bad,controls=commands,
        dropout_count=max(x['s']['clock_follow']['dropouts'] for x in states),
        states=sorted({x['s']['clock_follow']['state'] for x in states}),
        private_bytes_first=states[0]['private_bytes'],private_bytes_last=states[-1]['private_bytes'],
        relay_queue_max=max(x['relay_q'] for x in states),output_capture_queue_max=max(x['drain_q'] for x in states))
    if len(out)==len(ingress) and len(out):
        delay=(out-ingress)/1e6
        window=min(len(out)//2,600*48)
        result.update(ingress_to_egress_first_ms=describe(delay[:window]),ingress_to_egress_last_ms=describe(delay[-window:]))
    save(f/'result.json',result)
    return result
if __name__=='__main__':print(soak(Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN']),int(sys.argv[1])))

