import json,sys,time
from pathlib import Path
r=Path(__file__).resolve().parent
sys.path.insert(0,str(r.parent))
from desktop_sync import cmd
p=json.loads((r/'control.json').read_text())['port']
for _ in range(45):
 s=cmd(p,'transport.status')
 if s['position']==96000 and not s['playing']:
  print('Confirmed',s,flush=True);break
 time.sleep(1)
else: print(s,flush=True)
