from pathlib import Path
import json,time,sys
from analyse import np
import rtmidi
d=Path(__file__).resolve().parent
sys.path.insert(0,str(d.parent))
from desktop_sync import cmd
p=json.loads((d/'control.json').read_text())['port']
assert not cmd(p,'transport.status')['playing'] and not cmd(p,'transport.status')['recording']
mtc=cmd(p,'setup.mtc')
assert mtc['online'] and mtc['input']=='UM-ONE'
msg=[]
for line in (d.parent/'h-mtc-sd-20261121-211205'/'take1-wire.jsonl').read_text().splitlines():
 t,name,b=json.loads(line)
 if name.startswith('UM-ONE') and b[0]==241:
  if msg and t-msg[0][0]>6_500_000_000:break
  msg.append((t,b))
assert len(msg)>760
out=rtmidi.MidiOut()
ids=[i for i,name in enumerate(out.get_ports()) if name.startswith('Model 12 MIDI ')]
assert len(ids)==1
out.open_port(ids[0])
try:
 pos=[240,127,127,1,1,96,0,0,0,247]
 out.send_message(pos);time.sleep(.8)
 start=time.perf_counter()+.12
 for t,b in msg:
  deadline=start+(t-msg[0][0])/1e9
  delay=deadline-time.perf_counter()
  if delay>.001:time.sleep(delay-.0007)
  while time.perf_counter()<deadline:pass
  out.send_message(b)
 time.sleep(.6);out.send_message(pos);time.sleep(.6)
 print(len(msg),cmd(p,'setup.midi_sync_status')['mtc_chase']['state'],cmd(p,'transport.status'))
finally:out.close_port()
