import sys, json, wave
from pathlib import Path
from assess import np,matches,mono
here=Path(__file__).resolve().parent
name=sys.argv[1]
j=json.loads((here/(name+'.json')).read_text())
events=[(t,m) for t,n,m in j['midi'] if n.startswith('UM-ONE')]
start=next(t for t,m in events if m[0] in (250,251)); stop=next(t for t,m in events if t>start and m[0]==252)
clocks=np.array([t for t,m in events if start<=t<=stop and m[0]==248])
wire=60*(len(clocks)-1)/(24*(clocks[-1]-clocks[0]))
estimates=[f['estimated_bpm'] for t,tr,f in j['states'] if start+2<t<stop and tr['playing'] and f['estimated_bpm']]
def locate(x,fn):
    tmpl=mono(here/fn)[200:2100]
    corr=matches(x,tmpl)
    hits=np.flatnonzero(corr>.78)
    groups=np.split(hits,np.flatnonzero(np.diff(hits)>4800)+1) if len(hits) else []
    return [int(g[corr[g].argmax()])-200 for g in groups],round(float(corr.max()),4)
out=dict(wire_bpm=wire,clock_count=len(clocks),host_bpm_median=float(np.median(estimates)) if estimates else None,transport=[m for t,m in events if m[0]!=248],host_stopped=not j['states'][-1][1]['playing'])
for k,suffix in [('digital','.wav'),('main','-main.wav')]:
    x=mono(here/(name+suffix))
    sr=48000
    sn,sc=locate(x,'Snare.wav'); cr,cc=locate(x,'Crash.wav')
    out[k]=dict(snare_seconds=[round(i/sr,4) for i in sn],snare_score=sc,crash_count=len(cr),crash_score=cc,quarter_ms=float(np.median(np.diff(sn))/sr*500) if len(sn)>1 else None)
    hats,hat_score=locate(x,'Hat.wav')
    out[k]['hat_count']=len(hats);out[k]['hat_score']=hat_score
    if hats and cr: out[k]['last_hat_after_crash_s']=(hats[-1]-cr[0])/sr
    if k=='digital' and cr:
        b=j['blocks'];ends=np.cumsum([v[1] for v in b]);i=int(ends.searchsorted(cr[0],side='right'))
        out['crash_after_first_clk_s']=float(b[i][0]-(ends[i]-cr[0])/sr-clocks[0])
with wave.open(str(here/(name+'-keys-main.wav')),'rb') as w:
    y=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
    kt=json.loads((here/(name+'-keys-main-times.json')).read_text()); lens=np.array([n for _,n in kt]); bounds=np.r_[0,np.cumsum(lens)]; keep=[i for i,(t,n) in enumerate(kt) if start<=t<=stop]; assert keep; y=y[bounds[keep[0]]:bounds[keep[-1]+1]]
    out['CH2_peak_dbfs']=round(float(20*np.log10(max(np.max(np.abs(y)),1e-8))),1)
    pwr=np.sqrt(np.mean(y[:len(y)//480*480].reshape(-1,480)**2,axis=1))
    out['CH2_above_minus45dB_seconds']=round(float((pwr>.00562).sum()*.01),2)
(here/(name+'-result.json')).write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))


