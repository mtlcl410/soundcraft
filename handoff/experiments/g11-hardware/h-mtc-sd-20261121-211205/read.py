from pathlib import Path
import json,sys
from collections import Counter
r=Path(__file__).resolve().parent
label=sys.argv[1]
def read(s):
 f=r/(label+s)
 if not f.exists(): return []
 rows=[]
 for line in f.read_text(encoding='utf8').splitlines():
  try: rows.append(json.loads(line))
  except ValueError: pass
 return rows
wire=read('-wire.jsonl')
states=read('-transport.jsonl')
for name in sorted(set(w[1] for w in wire)):
 seen=[w for w in wire if w[1]==name and w[2][0]==241]
 full=[w for w in wire if w[1]==name and w[2][0]==240]
 print(name,len(seen),'QF',round((seen[-1][0]-seen[0][0])/1e9,4) if seen else None,'seconds;',len(full),'SysEx')
use=[s for s in states if 'transport' in s]
if use:
 print('state counts',Counter(s['mtc']['state'] for s in use),'recording',sum(bool(s['transport']['recording']) for s in use),'errors',sum('error'in s for s in states))
 print('last',use[-1]['mtc']['state'],use[-1]['mtc']['incoming_timecode'],use[-1]['transport'])
