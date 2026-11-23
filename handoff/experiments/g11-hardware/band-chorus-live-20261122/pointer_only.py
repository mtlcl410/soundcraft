import json, pathlib, sys, time
here=pathlib.Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent),str(here.parent/"capture-deps")]
from desktop_sync import cmd
import rtmidi
port=json.loads((here/"control.json").read_text())["port"]
spp=int(sys.argv[1]); assert spp in (64,65)
assert not cmd(port,"transport.status")["playing"]
out=rtmidi.MidiOut()
i,= [i for i,n in enumerate(out.get_ports()) if n.rsplit(" ",1)[0]=="Model 12 MIDI"]
out.open_port(i)
try:
    out.send_message([0xf2,spp,0])
finally:
    out.close_port()
time.sleep(.35)
status=cmd(port,"transport.status")
print(json.dumps(status)); assert not status["playing"] and status["position"]==spp*6000
