"""Check each physical return against the crash and subsequent accompaniment templates."""
from pathlib import Path
import json,sys
w=Path(__file__).resolve().parent; d=w.parent;sys.path.insert(0,str(d))
p=d/'measure.py';s=p.read_text(encoding='utf-8-sig');tag=sys.argv[1];assert tag.replace('-','').isalnum()
dest=w/('music-'+tag+'.json')
s=s.replace("(d/'metrics.json')","Path("+repr(str(dest))+")")
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
rows=json.loads(dest.read_bytes())
for case in sys.argv[1:]:
 sub=[r for name,r in rows.items() if name.startswith(case+'/')]
 assert len(sub)==6 and sum(r['spp']==64 for r in sub)==4
 for r in sub:
  assert r['crashes']==int(r['spp']==64) and r['later_corr']>.90 and r['clocks']==144 and r['serial_gaps']==[0,0],(case,r)
print('PASS',len(rows),'physical takes')

