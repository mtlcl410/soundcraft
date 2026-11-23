import sys,time,json
from pathlib import Path
here=Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent),str(here.parent/"capture-deps")]
import rtmidi
from desktop_sync import cmd
p=json.loads((here/"control.json").read_text())["port"]
assert not cmd(p,"transport.status")["playing"]
out=rtmidi.MidiOut()
ports=[i for i,n in enumerate(out.get_ports()) if n.rsplit(" ",1)[0]=="Model 12 MIDI" or n=="Model 12 MIDI"]
assert len(ports)==1
spp=int(sys.argv[1]) if len(sys.argv)>1 else 64
assert spp in (60,64,65)
out.open_port(ports[0])
try:
    out.send_message([242,spp,0])
    time.sleep(.5)
    state=cmd(p,"transport.status")
    print("SPP",spp,state,flush=True)
    if state["playing"] or state["position"]!=spp*6000:
        raise RuntimeError("exact SPP did not reach the host")
    print("WALL_ANCHOR",time.perf_counter_ns(),time.time_ns(),time.perf_counter_ns(),flush=True)
    out.send_message([251])
    origin=time.perf_counter()
    for n in range(144):
        time.sleep(max(0,origin+n/48-time.perf_counter()))
        out.send_message([248])
finally:
    out.send_message([252])
    out.close_port()
