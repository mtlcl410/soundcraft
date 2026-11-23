"""Record raw messages from available named test devices, each with the same host time."""
import sys,json,time,queue
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'capture-deps'))
import rtmidi
base=rtmidi.MidiIn()
ports=base.get_ports()
inputs=[]
q=queue.SimpleQueue()
def received(event,name):
    q.put((time.perf_counter_ns(),name,event[0]))
try:
    for i,name in enumerate(ports):
        if not ('Model 12' in name or 'UM-ONE' in name):
            continue
        p=rtmidi.MidiIn()
        p.ignore_types(sysex=False,timing=False,active_sense=True)
        try:
            p.open_port(i)
        except Exception as e:
            print(name,str(e),flush=True)
            continue
        p.set_callback(received,name)
        inputs.append(p)
        print('READY',name,flush=True)
    deadline=time.monotonic()+1800
    with (root/'wire.jsonl').open('a',encoding='utf8',buffering=1) as log:
        while time.monotonic()<deadline and not (root/'end-monitor').exists():
            try:
                item=q.get(timeout=.2)
                log.write(json.dumps(item)+'\n')
            except queue.Empty:
                pass
finally:
    for p in inputs:
        p.close_port()

