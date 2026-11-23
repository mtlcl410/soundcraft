"""Dedicated DIN bridge for the H-10 pilot. Buffer trace rows outside the send loop."""
from pathlib import Path
import csv,os,sys,time,queue
p=Path(sys.argv[1]); d=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(d/'midi'))
from midi_path import live_midi
import psutil
from array import array
psutil.Process().nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
marks=array('Q')
with live_midi(tx_name=sys.argv[2],rx_name='UM-ONE') as (tx,q,_):
    (p/'bridge-ready').touch()
    while True:
        try:t,m,_=q.get(timeout=.08)
        except queue.Empty:
            if (p/'bridge-stop').exists():break
            continue
        if m not in ((250,),(248,),(252,)):continue
        entry=time.perf_counter_ns();tx.send_message(list(m));end=time.perf_counter_ns()
        marks.extend((t,entry,end,m[0]))
with (p/'relay.csv').open('x',newline='') as f:
    w=csv.writer(f);w.writerow(('arrival_ns','entry_ns','return_ns','hex'))
    for i in range(0,len(marks),4):w.writerow((*marks[i:i+3],format(marks[i+3],'02x')))

