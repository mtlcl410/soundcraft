from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from inspect_dips import *
b=int(sys.argv[1]);tag=sys.argv[2];p=root/tag
r=read(p/'record.json');t=next(t for t,m in r['events'] if m==[248])+sum(r['anchors'])//2
w=read(root/f'audio-{tag}.json');a=load_wave(p/'out.bin');h=load_wave(p/'in.bin')
left=(int(a[np.searchsorted(a['ns'],t)]['serial'])-int(a[0]['serial']))*b
v=[]
for sec,step in w['residual_steps']:
 frame=round(sec*rate);k=left+frame;j=k+w['chunks'][frame//44096]['lag']
 x=segment(a,k-1200,3000,b)@gain;y=segment(h,j-1200,3000,b)
 ls=[local(x,y,s,96) for s in (-288,-96,0,96,288)]
 v.append(dict(s=sec,step=step,windows=ls))
Path(f'residual-{tag}.json').write_text(json.dumps(v,indent=2))
print(tag,[(round(r['s'],3),[(a['lag'],round(a['error'],1)) for a in r['windows']]) for r in v])
