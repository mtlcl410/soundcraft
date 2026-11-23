"""Fresh MTC timestamps over both physical DIN paths. No notes, audio or transport buttons."""
from pathlib import Path
import csv, json, sys, time, math
out=Path(__file__).resolve().parent; sys.path.insert(0,str(out.parent/'midi'))
from midi_path import live_midi,check_quiet
from wire_source import sleep_until
def quarter(frame):
    sec, f=divmod(frame,30)
    return [f&15, f>>4, sec&15, sec>>4,0,0,0,6]
runs=[]
with (out/'fresh-wire.csv').open('x',newline='') as file:
    csvout=csv.writer(file); csvout.writerow(('group','direction','message','sent_ns','received_ns'))
    for src,dst in [('UM-ONE','Model 12 MIDI'),('Model 12 MIDI','UM-ONE')]:
        with live_midi(src,dst) as (tx, box, ports):
            check_quiet(box,.35,lambda *_:None)
            for trial in range(3):
                # Model 12's observed first label is two frames beyond the stopped locate.
                baseframe=[0,0,900][trial]
                t0=time.perf_counter_ns()+100_000_000
                sent=[]
                for n in range(960):
                    sleep_until(t0+round(n*1e9/120))
                    b=(0xf1,(n%8)*16+quarter(baseframe+2+(n//8)*2)[n%8])
                    t=time.perf_counter_ns();tx.send_message(list(b));sent.append((b,t))
                time.sleep(.12); rx=[]
                while not box.empty():
                    stamp,msg,_=box.get_nowait()
                    if msg!=(0xfe,):rx.append((msg,stamp))
                assert [v[0] for v in sent]==[v[0] for v in rx],(ports,trial,len(rx))
                for (b,t),(_,recv) in zip(sent,rx):csvout.writerow((trial,src,bytes(b).hex(),t,recv))
                runs.append((src,trial,baseframe,[(int((recv-rx[0][1])//1000)+100_000,msg[1]) for msg,recv in rx]))
                print(ports,trial,len(rx),flush=True)
with (out/'fresh-inputs.txt').open('w') as file:
    for src,i,frame,ev in runs:
        for mode in ['rolling','located']:
            print(f'{src.replace(" ","")}{i} {mode} 30 {frame} 0 {frame*1600+12000}',file=file)
            print(' '.join(f'{t}:{v}' for t,v in ev),file=file)
            print(' '.join(str(round(i*256e6/48000)) for i in range(1550)),file=file)

