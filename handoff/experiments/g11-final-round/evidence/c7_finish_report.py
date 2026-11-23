"""Keep the acceptance link live after interactive tools close. Exit after strict gate completes."""
from pathlib import Path
import json,sys,time,subprocess,os
from datetime import datetime
import psutil
ev=Path(__file__).resolve().parent
gate=ev/'c7_native_control.py'; status=ev/'c7-idle-comparison.json'; report=ev/'C7-idle-reference.md'
worker_pid=int(sys.argv[1])
def state():return json.loads(status.read_text('utf8'))
def is_worker(pid):
 try:
  p=psutil.Process(pid)
  return any(Path(s).name==gate.name for s in p.cmdline())
 except (psutil.Error, OSError):return False
while True:
 try:
  data=state()
  if data.get('done'):
   subprocess.run([sys.executable,str(ev/'report_c7_control.py'),'idle'],cwd=ev,check=True)
   assert report.exists() and 'strict idle' in report.read_text('utf8') and '4,500' in report.read_text('utf8') or report.exists() and 'At least one software block' in report.read_text('utf8')
   print(f'{datetime.now().isoformat()} strict report verified at {report}',flush=True)
   break
  if not is_worker(worker_pid):
   with (ev/'c7-native-gate.log').open('a') as f:
    proc=subprocess.Popen([sys.executable,str(gate)],cwd=ev,stdout=f,stderr=f,creationflags=subprocess.CREATE_NO_WINDOW)
   worker_pid=proc.pid
   print(f'{datetime.now().isoformat()} resumed strict gate PID {worker_pid}',flush=True)
 except (json.JSONDecodeError, FileNotFoundError):
  pass
 time.sleep(15)
