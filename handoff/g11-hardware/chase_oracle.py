"""Independent 30-fps reference, output through Model 12 DIN to UM-ONE."""
from desktop_sync import *
sys.path.insert(0,str(root/'capture-deps'))
import rtmidi
port=json.loads((root/'mtc-control.json').read_text())['port']
out=rtmidi.MidiOut()
out.open_port(next(i for i,n in enumerate(out.get_ports()) if n.startswith('Model 12 MIDI')))
observations=[]
def observe():
    observations.append([time.monotonic(),cmd(port,'setup.mtc'),cmd(port,'transport.status')])
try:
    out.send_message([0xf0,0x7f,0x7f,1,1,0x60,0,10,0,0xf7])
    time.sleep(.25)
    observe()
    base=time.perf_counter()
    for i in range(192):
        t=300+2*(i//8)
        hh,ss=divmod(t//30,3600)
        mm,ss=divmod(ss,60)
        ff=t%30
        pieces=[ff&15,ff>>4,ss&15,ss>>4,mm&15,mm>>4,hh&15,(hh>>4)|6]
        until=base+i/120-time.perf_counter()
        if until>0: time.sleep(until)
        out.send_message([0xf1,16*(i%8)+pieces[i%8]])
        if i in (87,167): observe()
    time.sleep(.65)
    observe()
finally:
    out.close_port()
print(json.dumps(observations))
(root/'chase-independent.json').write_text(json.dumps(observations,indent=2))

