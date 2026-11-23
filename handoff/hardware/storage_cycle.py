"""One desktop for three physical STORAGE cycles. Never reopen SoundCraft's device between cycles."""
import csv, json, math, os, sys, threading, time, wave
from pathlib import Path
from manual_run import cmd, desktop, hw, live_midi, mtc, save, source
from m1 import np
from desktop_sync import rpc
from wire_source import sleep_until

def tone(path):
    sr=48000
    data=np.zeros(sr*12,dtype='<i2')
    k=np.arange(12000)
    env=np.minimum(1,k/96)*np.exp(-k/4800)
    data[5*sr:5*sr+len(k)]=np.rint(1200*env*np.sin(2*np.pi*440*k/sr)).astype('<i2')
    with wave.open(str(path),'wb') as w:
        w.setparams((1,2,sr,0,'NONE',''));w.writeframes(data.tobytes())

def reader(port, folder, end):
    with (folder/'recovery.jsonl').open('x',encoding='utf8',buffering=1) as w:
        while not end.is_set():
            row={'qpc_ns':time.perf_counter_ns()}
            try:
                ui=rpc(port,'ui.inspect',{})
                sync=cmd(port,'setup.midi_sync_status')
                row.update(device=ui.get('audio_device'),ui_status=ui.get('status'),chase=sync['mtc_chase'],output=sync['output'],transport=cmd(port,'transport.status'))
            except (OSError,ValueError) as exc:row['error']=str(exc)
            print(json.dumps(row),file=w);end.wait(.3)

def take(folder,port,label,rx):
    p=folder/label;p.mkdir()
    while not rx.empty():rx.get_nowait()
    save(p/'before.json',cmd(port,'setup.midi_sync_status'))
    source(p,'Model 12 MIDI',mtc('30',1))
    time.sleep(.8)
    with (p/'rx.csv').open('x',newline='') as file:
        rows=csv.writer(file);rows.writerow(['qpc_ns','hex'])
        while not rx.empty():
            stamp,msg,_=rx.get_nowait()
            if msg[0]!=254:rows.writerow([stamp,bytes(msg).hex()])
    save(p/'after.json',cmd(port,'setup.midi_sync_status'))
    result=offset(folder,p)
    save(p/'offset.json',result)
    return result

def offset(folder,part):
    with (part/'rx.csv').open() as f:
        qfs=[(int(r['qpc_ns']),int(r['hex'][2:],16)) for r in csv.DictReader(f) if r['hex'].startswith('f1')]
    if len(qfs)!=960: return dict(error='Unexpected quarter-frame count',count=len(qfs))
    anchors=[]
    for i,(stamp,msg) in enumerate(qfs):
        if msg>>4!=0 or i+7>=len(qfs):continue
        d=[v for _,v in qfs[i:i+8]]
        if [v>>4 for v in d]!=list(range(8)):return dict(error='Incomplete QF cycle')
        frame=(d[2]&15)*30+(d[0]&15)+16*(d[1]&15)
        if 120<=frame<=180:anchors.append(stamp/1e9-frame/30)
    if not anchors:return dict(error='No wire anchor at 5 s')
    target=float(np.median(anchors))+5
    result=dict(wire_count=len(qfs),anchor_qpc_s=target,wire_scatter_ms=float(np.ptp(anchors)*1000),channels={})
    for ep in sorted((folder/'driver').glob('epoch-*.json')):
        m=json.loads(ep.read_text())
        n=m['buffer'];hz=m['qpc_frequency'];sr=m['sample_rate']
        dtype=np.dtype([('p','<u8'),('system','<u8'),('qpc','<u8'),('seq','<u8'),('flags','<i4'),('n','<u4'),('x','<f4',(n,2))])
        raw=ep.with_suffix('.bin');size=raw.stat().st_size//dtype.itemsize
        if not size:continue
        a=np.memmap(raw,mode='r',dtype=dtype,shape=(size,))
        win=np.searchsorted(a['qpc'],np.array([target-.4,target+.5])*hz)
        if win[1]-win[0]<.7*sr/n:continue
        v=a[win[0]:win[1]]
        if np.any(np.diff(v['p'])!=n) or np.any(np.diff(v['seq'])!=1) or np.any((v['flags']&2)==0):
            return result|dict(error='Gap in measurement window',epoch=ep.stem)
        wav=v['x'].reshape(-1,2)
        for c,name in enumerate(('output1','input9')):
            ix=np.flatnonzero(abs(wav[:,c])>.0005)
            if not len(ix):continue
            i=int(ix[0])
            if i<512:continue
            end=min(i+2400,len(wav))
            run=wav[i:end,c]
            # Verify sustained A4 by counting positive-going crossings in the following 50 ms.
            crossings=np.count_nonzero((run[:-1]<=0)&(run[1:]>0))
            if not 20<=crossings<=23:continue
            obs=int(v['qpc'][i//n])/hz+(i%n)/sr
            result['channels'][name]=dict(ms=round((obs-target)*1000,4),epoch=ep.stem,crossings=int(crossings))
        break
    if len(result['channels'])!=2:result['error']='A4 absent or duplex driver capture unavailable'
    return result

def main(folder):
    wav=folder/'a4-at-5s.wav';tone(wav)
    with desktop(folder,wav) as port, live_midi(rx_name='UM-ONE') as (_,rx,_):
        cmd(port,'setup.mtc',input='UM-ONE',online=True,freewheel='frames',freewheel_frames=8)
        # Enable output timing compensation as specified; outbound Clock uses the opposite physical link.
        cmd(port,'setup.midi_beat_clock',destination='UM-ONE',offset=0,enabled=True)
        stop=threading.Event()
        obs=threading.Thread(target=reader,args=(port,folder,stop));obs.start()
        try:
            baseline=take(folder,port,'baseline',rx)
            if 'error' in baseline:raise RuntimeError(baseline)
            for j in range(1,4):
                # Keep rolling while the operator enters STORAGE. The source is the independent tool.
                pending=folder/f'cycle-{j}-restored';deadline=time.monotonic()+600
                k=0
                while not pending.exists():
                    if time.monotonic()>deadline:raise TimeoutError('STORAGE cycle incomplete')
                    k+=1
                    window=folder/f'cycle-{j}-rolling-{k}';window.mkdir()
                    try:
                        with live_midi(tx_name='Model 12 MIDI') as (tx,_,_):
                            t0=time.perf_counter_ns()
                            for due,message,tag in mtc('30',1):
                                if pending.exists():break
                                sleep_until(t0+due);tx.send_message(list(message))
                                if tag.endswith(':qf-24') and not (folder/f'cycle-{j}-ready').exists():
                                    (folder/f'cycle-{j}-ready').touch()
                    except Exception as exc:
                        save(window/'source-unavailable.json',dict(error=str(exc)));time.sleep(1)
                    while not rx.empty():rx.get_nowait()
                time.sleep(2)
                probe=take(folder,port,f'post-{j}',rx)
                if 'error' not in probe:
                    probe['difference_from_baseline_ms']={name:round(v['ms']-baseline['channels'][name]['ms'],4) for name,v in probe['channels'].items()}
                    probe['within_3ms']=all(abs(v)<=3 for v in probe['difference_from_baseline_ms'].values())
                save(folder/f'cycle-{j}-result.json',probe)
            cmd(port,'setup.midi_beat_clock',enabled=False)
            cmd(port,'setup.mtc',online=False)
            cmd(port,'transport.stop')
        finally:
            stop.set();obs.join(3)
if __name__=='__main__':main(Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN']))

