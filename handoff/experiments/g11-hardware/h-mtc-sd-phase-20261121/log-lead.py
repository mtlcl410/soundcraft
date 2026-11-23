from pathlib import Path
import sys,time,json
d=Path(__file__).resolve().parent
sys.path.insert(0,str(d.parent))
from desktop_sync import cmd
p=json.loads((d/'control.json').read_text())['port']
name=sys.argv[1]
with (d/(name+'-lead.jsonl')).open('x',buffering=1) as f:
 until=time.monotonic()+1100
 while not (d/name/'end.flag').exists() and time.monotonic()<until:
  r={'qpc_s':time.perf_counter()}
  try:
   s=cmd(p,'setup.midi_sync_status');r.update(lead=s['output']['reported_lead_us'],clamps=s['output']['lead_clamps'],state=s['mtc_chase']['state'],timecode=s['mtc_chase']['incoming_timecode'])
  except Exception as e:r['error']=str(e)
  f.write(json.dumps(r)+'\n');time.sleep(.45)
