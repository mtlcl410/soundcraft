from quality import *
r=json.loads((d/'metrics.json').read_text())
for path,v in r.items():
 if not v['drop_windows']:continue
 p=d/path;x=stereo(p.with_name(p.name+'-out.wav'));y=stereo(p.with_name(p.name+'-in.wav'));lag=v['lag_frames'];x=x[max(-lag,0):]@np.array(v['transfer']);y=y[max(0,lag):];n=min(len(x),len(y))//64*64
 def rms(a):return np.sqrt((a[:n].reshape(-1,64,2)**2).mean(axis=(1,2)))
 a=rms(x);b=rms(y);ii=np.flatnonzero((a>30)&(b<.2*a))*64
 for i in ii:
    u=y[i:i+64];j=int(np.argmin([np.sqrt(((x[i+off:i+off+64]-u)**2).mean()) for off in range(-256,257)]))-256
    print(path,i, 'RMS expected',a[i//64],'observed',b[i//64],'peak',abs(u).max(),'best lag shift',j)

