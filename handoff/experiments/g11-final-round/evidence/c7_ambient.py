from pathlib import Path
from datetime import datetime
import psutil, time, json
p=Path(__file__).resolve().parent
last=''
with(p/'c7-ambient.csv').open('w',encoding='ascii') as out:
 out.write('start,end,all_logical_cpu_percent\n')
 for _ in range(3600):
  start=datetime.now().isoformat(timespec='milliseconds')
  cpu=psutil.cpu_percent(interval=1)
  out.write(f'{start},{datetime.now().isoformat(timespec="milliseconds")},{cpu}\n');out.flush()
  try:
   state=json.loads((p/'c7-idle-comparison.json').read_text())
   if state.get('done'):break
  except (ValueError,FileNotFoundError):pass
