from quality import *
d=Path(__file__).resolve().parent
rows=json.loads((d/'metrics.json').read_text())
for key,r in rows.items():
 if not r['steps_over_32'] and not r['drop_windows']: continue
 p=d/key
 x=stereo(p.with_name(p.name+'-out.wav'));y=stereo(p.with_name(p.name+'-in.wav'));lag=r['lag_frames'];x=x[max(-lag,0):];y=y[max(lag,0):];n=min(len(x),len(y));x=x[:n]@np.array(r['transfer']);y=y[:n]
 q=np.flatnonzero(np.max(abs(np.diff(y-x,axis=0)),axis=1)>32)
 for g in np.split(q,np.flatnonzero(np.diff(q)>256)+1) if len(q) else []:
    i=max(0,int(g[0])-4);j=min(n,int(g[-1])+5)
    print(key,'aligned time',round(i/44100,3),'length',j-i,'rms forecast/return',round(np.sqrt((x[i:j]**2).mean()),1),round(np.sqrt((y[i:j]**2).mean()),1))
    for k in range(i,j,128):
        scores=[np.sqrt(((x[k+off:k+off+64]-y[k:k+64])**2).mean()) for off in range(-512,513)]
        pos=np.argmin(scores);print(k,pos-512, round(scores[pos],1),end=' | ')
    print()

