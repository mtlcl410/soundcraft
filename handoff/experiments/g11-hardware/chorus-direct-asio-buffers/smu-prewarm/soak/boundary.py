"""Use the existing local acceptance criteria, keeping earlier result files intact."""
from pathlib import Path
import json,sys
root=Path(__file__).resolve().parent;d=root.parent.parent
sys.path.insert(0,str(d))
cases=['soak-cold'+buf+'-'+str(k) for buf in ('64','128') for k in range(1,6)]
if len(sys.argv)>1:cases=[c for c in cases if c.startswith('soak-cold'+sys.argv[1]+'-')]
target=root/('boundary-'+str(len(cases))+'-'+cases[0]+'.json')
p=d/'measure.py'
source=p.read_text(encoding='utf-8-sig').replace("(d/'metrics.json')","Path("+repr(str(target))+")")
sys.argv[1:]=cases
exec(compile(source,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
r=json.loads(target.read_bytes())
assert len(r)==2*len(cases)
assert all(v['clocks']==144 and v['crashes']==int(v['spp']==64) and v['later_corr']>.90 for v in r.values())
print('PASS each boundary and subsequent note')

