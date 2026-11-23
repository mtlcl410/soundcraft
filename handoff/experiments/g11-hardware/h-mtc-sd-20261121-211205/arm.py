from pathlib import Path
import json,sys,time
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base.parent))
from desktop_sync import cmd
p=json.loads((base/'control.json').read_text())['port']
print('app',p,cmd(p,'setup.mtc',input='UM-ONE',online=True,freewheel='frames',freewheel_frames=8))
time.sleep(.75)
proof={c:cmd(p,c) for c in ('setup.mtc','setup.session','ui.audio_device','setup.mtc_output','transport.status')}
print('checked',proof['setup.mtc'],proof['transport.status'])
for c in ('transport.status','setup.midi_clock_follow'):
 try: print('other pre-existing desktop:',c,cmd(49894,c))
 except Exception as err: print('other:',str(err)[:180])
(base/'reader-arm.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False))
assert proof['setup.mtc']['online'] and proof['setup.mtc']['status']!='Input unavailable'
assert not proof['transport.status']['recording']
