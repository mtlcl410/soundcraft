from pathlib import Path
import sys,json
d=Path(__file__).resolve().parent
rows=[]
for ln in (d/(sys.argv[1]+'-wire.jsonl')).read_text().splitlines():
 try:t,p,b=json.loads(ln)
 except ValueError:continue
 if p.startswith('UM-ONE') and b[0]==241:
  if not rows or t-rows[-1][-1]>700000000:rows.append([])
  rows[-1].append(t)
print([(len(x),round((x[-1]-x[0])/1e9,2)) for x in rows])
