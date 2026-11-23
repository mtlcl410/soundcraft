from pathlib import Path
import sys,json,subprocess,time
ev=Path(__file__).resolve().parent; sys.path.insert(0,str(ev.parent))
from desktop_sync import cmd
port=json.loads((ev/'control.json').read_text())['port']
print(cmd(port,'setup.mtc',input='UM-ONE',online=False),flush=True)
with (ev/'port-check.log').open('w') as log:
 p=subprocess.Popen([sys.executable,'-X','utf8',str(ev/'capture.py'),'port-check'],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  for _ in range(60):
   if (ev/'port-check-wire.jsonl').exists() or p.poll() is not None: break
   time.sleep(.1)
 finally:
  (ev/'port-check.end').touch()
  p.wait(12)
print((ev/'port-check.log').read_text())
if p.returncode: raise SystemExit(p.returncode)
