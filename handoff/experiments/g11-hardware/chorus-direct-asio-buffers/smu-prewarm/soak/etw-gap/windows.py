from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from timing import *
b=int(sys.argv[1]);tag=sys.argv[2] if len(sys.argv)>2 else str(b);p=root/(tag if tag.startswith('usb') else f'sched{b}');r=read(p/'record.json')
a=load_profile(p/'profile.bin').astype(np.int64)
anchor=sum(r['anchors'])//2
lo,hi=np.searchsorted(a[:,1],[next(t+anchor for t,m in r['events'] if m==[v]) for v in [248,252]])
v=a[lo:hi];starts=v[:,1]-v[:,2];g=starts[1:]-v[:-1,1]
assert (np.diff(v[:,0])==1).all() and ((v[:,7]&4095)==b).all()
rows=[]
for i in np.argsort(g)[-24:][::-1]:
    rows.append([int(v[i,0]),int(v[i,1]),int(starts[i+1]),float(g[i]/1e6)])
here=Path(__file__).resolve().parent
(here/f'windows-{tag}.txt').write_text('\n'.join(f'{end} {start}' for _,end,start,_ in rows))
(here/f'gaps-{tag}.json').write_text(json.dumps(dict(pid=read(p/'control.json')['pid'],callbacks=len(v),above6099=int((g>=6099000).sum()),anchor_change_ns=r['anchors'][1]-r['anchors'][0],percentiles=np.percentile(g,[50,99,99.9,100]).tolist(),max_work_ms=float(v[:,2].max()/1e6),over=int((v[:,2]>b/44100*1e9).sum()),rows=rows),indent=2))
with (here/f'windows-{tag}.txt').open('a') as f:
    for cb in sorted(v[v[:,2]>b/44100*1e9],key=lambda row:-row[2])[:20]:f.write(f'\n{cb[1]-cb[2]} {cb[1]}')
print(len(v),rows[:3])


