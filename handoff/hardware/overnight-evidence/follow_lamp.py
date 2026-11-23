"""Five physical DIN loss/reacquire cycles. Measure the control state shared with the EXT display."""
import os
from pathlib import Path
import sys
import threading
import time

a=Path(__file__).resolve().parent
d=a.parent
sys.path.insert(0,str(d))
from manual_run import cmd,desktop,live_midi,save
from wire_source import sleep_until

def probe(folder):
    traces=[]
    with desktop(folder,None) as port:
        missing=None
        try:
            cmd(port,'setup.midi_clock_follow',input=None,enabled=True)
        except ValueError as exc:
            missing=str(exc)
        assert missing and 'Select a MIDI clock input' in missing, missing
        for iteration in range(5):
            if iteration:
                cmd(port,'setup.midi_clock_follow',enabled=False,input=None)
            initial=cmd(port,'setup.midi_clock_follow',input='UM-ONE',enabled=True,loss_policy='coast')
            assert initial['state']=='Waiting',initial
            log=[]; err=[]; stop=threading.Event()
            def read():
                try:
                    while not stop.is_set():
                        before=time.perf_counter_ns()
                        data=cmd(port,'setup.midi_clock_follow')
                        log.append([before,time.perf_counter_ns(),data['state'],data['dropouts']])
                        stop.wait(.012)
                except Exception as ex:
                    err.append(str(ex))
            poll=threading.Thread(target=read);poll.start()
            sent=[]
            def send(name,message,conn):
                before=time.perf_counter_ns();conn.send_message([message]);sent.append((name,before,time.perf_counter_ns()))
            try:
                with live_midi(tx_name='Model 12 MIDI') as (tx,_,_):
                    origin=time.perf_counter_ns()+100_000_000
                    sleep_until(origin);send('start',250,tx)
                    for i in range(72):
                        sleep_until(origin+round(i*1e9/48))
                        send('initial',248,tx)
                # Closing the sending handle leaves the receiving interface and cables intact.
                sleep_until(sent[-1][2]+400_000_000)
                with live_midi(tx_name='Model 12 MIDI') as (tx,_,_):
                    origin=time.perf_counter_ns()
                    for i in range(72):
                        sleep_until(origin+round(i*1e9/48))
                        send('resume',248,tx)
                    sleep_until(origin+round(72*1e9/48));send('stop',252,tx)
                    time.sleep(.40)
            finally:
                stop.set();poll.join(10)
            changes=[]
            for entry in log:
                if not changes or entry[2]!=changes[-1][2]:changes.append(entry)
            resumes=[v[1] for v in sent if v[0]=='resume']
            locked=[v for v in changes if v[2]=='Locked' and resumes and v[1]>=resumes[0]]
            traces.append(dict(iteration=iteration+1,sent=sent,polls=log,changes=changes,
                observed_states=[v[2] for v in changes],errors=err,
                first_observed_relock_ms=(locked[0][1]-resumes[0])/1e6 if locked else None))
            save(folder/'cycles.json',dict(missing_source=missing,cycles=traces))
        cmd(port,'setup.midi_clock_follow',enabled=False,input=None)
    expected=['Waiting','Locked','Coasting','Locked','Stopped']
    bad=[t['iteration'] for t in traces if t['observed_states']!=expected or t['errors']]
    save(folder/'result.json',dict(cycles=len(traces),failed=bad,expected=expected,
         observed=[t['observed_states'] for t in traces],relock_observed_ms=[t['first_observed_relock_ms'] for t in traces],
         scope='physical DIN and shared EXT state observed through app control RPC; timing includes polling and UI dispatch'))
    assert not bad,bad

if __name__=='__main__':
    probe(Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN']))
