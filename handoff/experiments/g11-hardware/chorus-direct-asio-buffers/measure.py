from pathlib import Path
import json,sys
from quality import quality,stereo,np
d=Path(__file__).resolve().parent
prior=d.parent/'chorus-direct-asio'
sys.path.insert(0,str(prior))
from assess import matches,mono
def read(f):return json.loads(f.read_bytes())
rate=44100
off=round(200*rate/48000)
template=np.interp(np.arange(off,round(2600*rate/48000))*48000/rate,np.arange(len(mono(prior/'Crash.wav'))),mono(prior/'Crash.wav'))
ref=d.parent/'chorus-latency-1675-fixed'
s=read(ref/'monitor-reference-analysis.json')['crash_recording_frames'][0]+24000
follow=np.interp(np.arange(0,2399,48000/rate),np.arange(2400),mono(ref/'monitor-reference.wav')[s:s+2400])
rows={}
for case in sys.argv[1:]:
 p=d/case
 for f in sorted(p.glob('*-in.wav')):
    name=f.name[:-7];j=read(p/(name+'.json'));ev=j['events'];sp=j['spp'];b=j['in']['size']
    assert [m for t,m in ev if m[0]!=248]==[[242,sp,0],[251],[252]]
    ticks=[t for t,m in ev if m[0]==248];assert len(ticks)==144 and not j['final']['playing']
    x=stereo(f.with_name(name+'-out.wav'));y=stereo(f);score=matches(y.mean(1),template)
    hits=np.flatnonzero(score>.9);groups=np.split(hits,np.flatnonzero(np.diff(hits)>.1*rate)+1) if len(hits) else []
    r=quality(x,y);lag=r['lag_frames'];ix=max(0,-lag);iy=max(0,lag);n=min(len(x)-ix,len(y)-iy)
    pred=x[ix:ix+n]@np.array(r['transfer']);obs=y[iy:iy+n]
    res=obs-pred;step=np.max(abs(np.diff(res,axis=0)),axis=1)
    r.update(peak_residual_step=float(step.max()),steps_over_32=int((step>32).sum()),clipped_frames=int((abs(y)>=32767).any(1).sum()),serial_gaps=[j[k]['serial_gaps'] for k in ('in','out')],crashes=len(groups),crash_corr=round(float(score.max()),5),later_corr=round(float(matches(y.mean(1),follow).max()),5),spp=sp,clocks=len(ticks),size=b)
    if groups:
        g=groups[0];idx=int(g[score[g].argmax()])-off
        assert len(j['in']['adc'])==1
        r['ms']=round(((j['in']['ns'][idx//b]-j['in']['adc'][0])/1e9+idx%b/rate-ticks[0])*1000,3)
    # Positive controls on copies, at a strong part of the signal; same gain and thresholds.
    peak=int(np.argmax(abs(pred).max(1))//64*64);test=obs.copy();test[peak:peak+64]=0;test[peak+80,0]+=256
    assert (np.max(abs(np.diff(test-pred,axis=0))[peak+79:peak+81])>32 and np.sqrt((pred[peak:peak+64]**2).mean())>30 and np.sqrt((test[peak:peak+64]**2).mean())==0)
    rows[case+'/'+name]=r
    print(case,name,r.get('ms'),len(groups),r['later_corr'],r['peak_residual_step'],r['drop_windows'],r['serial_gaps'])
(d/'metrics.json').write_text(json.dumps(rows,indent=2))

