"""Paced external reference with no filesystem or UI calls in the timed section."""
from pathlib import Path
from array import array
import csv,json,os,sys,time
import psutil
p=Path(sys.argv[1]); secs=int(sys.argv[2]); d=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(d/'midi'));from midi_path import live_midi
from wire_source import sleep_until
psutil.Process().nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
n=secs*48; sent=array('Q',[0])*n
advance_ms=int(os.environ.get('SC_AUDIT_STOP_ADVANCE_MS','0'))
if not 0<=advance_ms<=19: raise ValueError('Stop must follow the final 120 BPM pulse')
with live_midi(tx_name='Model 12 MIDI') as (tx,_,_):
    origin=time.perf_counter_ns()+500_000_000
    sleep_until(origin);tx.send_message([250])
    try:
        for i in range(n):
            deadline=origin+round(i*1e9/48)
            sleep_until(deadline);sent[i]=time.perf_counter_ns();tx.send_message([248])
        stop_deadline=origin+secs*1_000_000_000-advance_ms*1_000_000
        sleep_until(stop_deadline)
    finally:
        stop_begin=time.perf_counter_ns()
        tx.send_message([252])
        stop_end=time.perf_counter_ns()
(p/'source-stop.json').write_text(json.dumps(dict(advance_ms=advance_ms,due_ns=stop_deadline,begin_ns=stop_begin,end_ns=stop_end)))
with (p/'source.csv').open('x',newline='') as f:
    w=csv.writer(f);w.writerow(['due_ns','send_ns','hex']);w.writerows((origin+round(i*1e9/48),t,'f8') for i,t in enumerate(sent) if t)

