from pathlib import Path
import json, sys, time
from sequence import root,output,guarded
for _ in range(7200):
    if (root/'panel-buffer-restored.json').exists():break
    time.sleep(2)
else:raise TimeoutError('audio ruler unfinished')
for side,tx,rx in [('reverse','Model 12 MIDI','UM-ONE'),('forward','UM-ONE','Model 12 MIDI')]:
    for suffix in ('c','d','e'):
        if any(json.loads(p.read_text())['environment_valid'] for p in output.glob(f'm2-{side}-*/environment-result.json')):break
        name=f'm2-{side}-{suffix}'
        ok=guarded(name,[sys.executable,root/'midi/midi_path.py','run','--tx',tx,'--rx',rx,'--out',output/name/'data'])
        if ok:break
import report
