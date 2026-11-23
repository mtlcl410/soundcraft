from pathlib import Path
from queue import SimpleQueue, Empty
import json, time, sys, threading, datetime
run=Path(__file__).resolve().parent
sys.path[:0]=[str(run.parent),str(run.parent/'capture-deps')]
import rtmidi
from desktop_sync import cmd
port=json.loads((run/'control.json').read_text())['port']
label=sys.argv[1]
wirefile=run/(label+'-wire.jsonl')
statefile=run/(label+'-transport.jsonl')
end=run/(label+'.end')
q=SimpleQueue()
inputs=[]
quitflag=threading.Event()
def read_states():
 with statefile.open('x',encoding='utf-8',buffering=1) as out:
  while not quitflag.is_set():
   row={'monotonic_ns':time.perf_counter_ns()}
   try:
    row['mtc']=cmd(port,'setup.midi_sync_status')['mtc_chase']
    row['transport']=cmd(port,'transport.status')
   except (OSError,ValueError) as e: row['error']=str(e)
   row['reply_ns']=time.perf_counter_ns()
   out.write(json.dumps(row)+'\n')
   quitflag.wait(.06)
def receive(ev,name):
 msg=ev[0]
 if msg and msg[0] in (240,241,250,251,252): q.put((time.perf_counter_ns(),name,msg))
try:
 names=rtmidi.MidiIn().get_ports()
 for prefix in ['UM-ONE ', 'Model 12 MIDI ']:
  idx=next((i for i,n in enumerate(names) if n.startswith(prefix)),None)
  if idx is None: print('Missing:',prefix,flush=True);continue
  m=rtmidi.MidiIn()
  m.ignore_types(sysex=False,timing=False,active_sense=True)
  try: m.open_port(idx)
  except Exception as err: print('Open error',names[idx],err,flush=True);continue
  m.set_callback(receive,names[idx])
  inputs.append(m)
  print('OPEN',names[idx],flush=True)
 if not inputs: raise RuntimeError('No capture port could be opened')
 thread=threading.Thread(target=read_states)
 thread.start()
 with wirefile.open('x',encoding='utf-8',buffering=1) as out:
  print('READY',label,datetime.datetime.now().isoformat(),flush=True)
  until=time.monotonic()+15*60
  while not end.exists() and time.monotonic()<until:
   try: item=q.get(timeout=.1)
   except Empty: continue
   out.write(json.dumps(item)+'\n')
finally:
 quitflag.set()
 if 'thread' in locals(): thread.join()
 for m in inputs: m.close_port()
