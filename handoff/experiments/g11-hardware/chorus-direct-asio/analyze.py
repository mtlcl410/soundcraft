from pathlib import Path
import json, statistics, wave, sys
from assess import mono,matches,np
d=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_bytes())
rate=44100
def resample_window(x,start,end):
    offset=round(start*rate/48000)
    pos=np.arange(offset,round(end*rate/48000))*48000/rate
    return offset,np.interp(pos,np.arange(len(x)),x)
off,template=resample_window(mono(d/'Crash.wav'),200,2600)
ref=d.parent/'chorus-latency-1675-fixed';s=read(ref/'monitor-reference-analysis.json')['crash_recording_frames'][0]+24000
follow=np.interp(np.arange(0,2399,48000/rate),np.arange(2400),mono(ref/'monitor-reference.wav')[s:s+2400])
rows={}
for name in ('exact-a','late-a','exact-b','exact-c','late-b','exact-d'):
 j=read(d/(name+'.json'));sp=j['spp'];events=j['midi'];ctrl=[m for t,m in events if m[0]!=248];assert ctrl==[[242,sp,0],[251],[252]],ctrl
 ticks=[t for t,m in events if m[0]==248];assert len(ticks)==144
 f8=ticks[0];x=mono(d/(name+'.wav'));ts=j['blocks'];ends=np.cumsum([b[1] for b in ts])
 assert len(x)==ends[-1] and not j['transport']['playing']
 score=matches(x,template);hits=np.flatnonzero(score>.90)
 groups=np.split(hits,np.flatnonzero(np.diff(hits)>rate*.1)+1) if len(hits) else []
 assert len(groups)==int(sp==64),(name,len(groups),float(score.max()))
 music=float(matches(x,follow).max());assert music>.90,(name,music)
 blocks=[m for m in ts if f8-.02<m[0]<events[-1][0]+.12]
 assert blocks and all(m[1]==256 and not m[3] for m in blocks)
 v=dict(spp=sp,clock_count=len(ticks),crash_count=len(groups),best_crash_correlation=float(score.max()),later_correlation=music,adc_adjustment_ms=float(np.median([m[2] for m in blocks])*1000))
 if groups:
    g=groups[0];idx=int(g[score[g].argmax()])-off;i=int(ends.searchsorted(idx,side='right'));m=ts[i]
    v['first_clock_to_main_ms']=round((m[0]+m[2]+(idx-ends[i]+m[1])/rate-f8)*1000,3)
 rows[name]=v
print(json.dumps(rows,indent=2));(d/'per-take.json').write_text(json.dumps(rows,indent=2))

