"""Fit a single insertion between two independently waveform-matched flanks."""
from analyse_replay import *
def fit(x,y,shift):
    # Signals share a post-event sample origin; x has another shift samples of tail.
    n=len(y);xpost=x[:n];xpre=x[shift:shift+n]
    def pref(s):return np.r_[0.,np.cumsum((s*s).sum(axis=1))]
    a=pref(y-xpre);b=pref(y);c=pref(y-xpost)
    ix=np.arange(128,n-shift-128);end=ix+shift
    err=a[ix]+b[end]-b[ix]+c[-1]-c[end]
    i=int(ix[err.argmin()]);k=i+shift
    residual=np.vstack((y[:i]-xpre[:i],y[k:]-xpost[k:]))
    return dict(length=shift,index=i,quiet_rms=rms(y[i:k]) if shift else None,
                preceding_rms=rms(y[i-64:i]),following_rms=rms(y[k:k+64]),
                before_error=rms(y[i-128:i]-xpre[i-128:i]),after_error=rms(y[k:k+128]-xpost[k:k+128]),
                flank_rms=rms(residual),join_jump=float(np.max(abs((y[k]-y[i-1])-(xpost[k]-xpre[i-1])))),
                fit_rms=float(np.sqrt(max(0.,err.min())/(n*2))))
if __name__=='__main__':
    out={}
    for b in (64,128):
        z=np.load(here/f'replay-{b}.npz');x=z['source'].astype(float)*32768@gain;y=z['recording'].astype(float)*32768
        rows=read(here/f'independent-{b}.json')
        for v,t in zip(rows,z['targets']):
            post=v['post_lag'];sh=post-v['pre_lag'];assert 0<=sh<512
            span=1024;i=16384-span;j=t+post-span
            v['fit']=fit(x[i:i+2*span+sh],y[j:j+2*span],sh)
            print(b,v['held'],v['fit']['length'],*[round(v['fit'][k] or 0,2) for k in ['quiet_rms','flank_rms','before_error','after_error']])
        out[str(b)]=rows
    p=root/'long64';q=read(here/'original.json')[0];i=q['output_frame'];j=q['input_frame']
    x=segment(load_wave(p/'out.bin'),i-768,1536+107,64)@gain;y=segment(load_wave(p/'in.bin'),j-768,1536,64)
    out['original']=fit(x,y,107);assert out['original']['index']==768-43 and out['original']['flank_rms']<2
    # Data-independent signal with a known insertion checks alignment and units.
    g=np.random.default_rng(296);x=g.normal(0,90,(1200,2));q=307;sh=73
    # With the post-event origin, source starts at x[sh] and resumes at x[q+sh].
    y=np.vstack([x[sh:sh+q],np.zeros((sh,2)),x[q+sh:1000]])
    chk=fit(x[:len(y)+sh],y,sh);assert chk['index']==q and chk['flank_rms']<1e-9
    (here/'splices.json').write_text(json.dumps(out,indent=2))

