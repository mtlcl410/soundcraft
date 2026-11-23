"""Match the original 486 s musical attack to the fresh digital and MAIN streams."""
from pathlib import Path
import sys,json
here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parent/'dip486'))
from original import align,segment,root,gain,load_wave,read,np,rms
b=int(sys.argv[1]);tag=sys.argv[2]
p=root/tag;rec=read(p/'record.json')
out,main=[load_wave(p/f'{n}.bin') for n in ('out','in')]
origin=next(t for t,m in rec['events'] if m==[248])+sum(rec['anchors'])//2
def frame(w,t):
 i=np.searchsorted(w['ns'].astype(np.int64),t)
 return (int(w[i]['serial'])-int(w[0]['serial']))*b
f0=read(root/'dip486'/'original.json')[0]['output_frame']
ref=segment(load_wave(root/'long64'/'out.bin'),f0-64,640,64)
prior=frame(out,origin+486242000000)-10000
sig=segment(out,prior,21000,b)
offset,sim=align(sig,ref)
landmarks=[align(sig,ref[l:r])[0]-l for l,r in [(0,128),(128,384),(384,640)]]
f=prior+offset+64;sample=segment(out,f-64,640,b)@gain
ts=int(out[np.searchsorted(out['serial'],int(out[0]['serial'])+f//b)]['ns'])
search=frame(main,ts)-3072
shift,score=align(segment(main,search,8000,b),sample);g=search+shift+64
s=segment(main,g-64,640,b)
z=dict(output_score=sim,landmarks_relative=[k-offset for k in landmarks],main_score=score,
    previous_music_position_wall_s=(ts-origin)/1e9,out_frame=f,main_frame=g,utc_ns=ts,
    rms_expected=rms(sample[64:128]),rms_main=rms(s[64:128]),error=rms(s[64:128]-sample[64:128]),
    error_full640=rms(s-sample),verified=bool(sim>.95 and max(abs(k-offset) for k in landmarks)<=3 and score>.95))
Path(f'landmark-{tag}.json').write_text(json.dumps(z,indent=2))
if z['verified']:
 with Path(f'windows-{tag}.txt').open('a') as h:h.write(f'\n{ts} {ts}\n')
print(z)
