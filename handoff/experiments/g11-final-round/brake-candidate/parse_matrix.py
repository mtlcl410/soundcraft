from pathlib import Path
import re,ast,sys
s=Path(sys.argv[1]).read_text(encoding='utf-8')
for nm,v in re.findall(r'HITS (\S+) (\[\[.*?\]\])',s,re.S):
 if 'Jitter' not in nm: continue
 x=ast.literal_eval(''.join(v.splitlines())); cut=int(nm.split('-')[2])//12
 off=x[cut+1][0];after=max(abs(y) for xx in x[cut+2:] for y in xx)
 if abs(off)>480 or after>288 or '120-100-396' in nm: print(nm,off,after,x[cut:cut+8])
