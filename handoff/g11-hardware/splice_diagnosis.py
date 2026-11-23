from acquisition_analysis import *
ref='smu-phase-reference-1795133302896796600'
old='smu-phase-live-1795135386595720400'
def waveform(base, when=10):
    a=json.loads((root/(base+'-acquisition.json')).read_text())
    d=json.loads((root/(base+'.json')).read_text())
    n=Tap(list(records(root/(base+'-native.bin'))),d['wall_qpc_offset_ns'])
    note=next(row for row in a['notes'] if row['score_seconds']==when)
    t=note['qpc'];k=np.searchsorted(n.dev,t,side='right')-1
    i=n.starts[k]+round((t-n.dev[k])*rate)
    return n.y[i-2400:i+16800],note
def hzfft(y,f0=349.228):
    size=32768
    sp=abs(np.fft.rfft(np.hanning(len(y))*y,size))
    k0=round(f0*size/rate)
    k=np.argmax(sp[k0-10:k0+11])+k0-10
    l,m,r=np.log(np.maximum(sp[k-1:k+2],1e-20))
    return (k+0.5*(l-r)/(l-2*m+r))*rate/size
def autocorr_hz(y,f0=349.228):
    # Normalized time-domain period; symmetric paired windows eliminate slope-amplitude bias.
    lag0=int(rate/f0)
    lags=np.arange(lag0-9,lag0+10)
    n=len(y)-lags[-1]-2
    w=np.hanning(n)
    def score(lag):
        j=(len(y)-n-lag)//2
        x=y[j:j+n]*w; z=y[j+lag:j+lag+n]*w
        return np.dot(x,z)/np.sqrt(np.dot(x,x)*np.dot(z,z))
    scores=np.array([score(l) for l in lags]);i=scores.argmax()
    l,m,r=scores[i-1:i+2];lag=lags[i]+.5*(l-r)/(l-2*m+r)
    return rate/lag
def window(x,ms,length):
    center=2400+round(ms*48)
    return x[center-length//2:center+length//2]
def cents(a,b):return 1200*np.log2(a/b)
def anchor(x,y,ms):
    # Disjoint 10 ms template; the held-out 42.67 ms pitch window is never searched for the best fit.
    z=window(x,ms,480)
    candidates=window(y,ms,1920)
    energy=np.convolve(candidates*candidates,np.ones(len(z)),'valid')
    scores=np.correlate(candidates,z)/np.sqrt(energy*np.dot(z,z))
    k=int(np.argmax(scores))
    return {'ms':ms, 'shift':k-720, 'correlation':round(float(scores[k]),7)}

def estimate(base,when):
    x,_=waveform(base,when);y,_=waveform(ref,when)
    anchors=[anchor(x,y,t) for t in [0,5,12,20,25,80,100]]
    # Estimate the shift once at 80 ms and independently confirm it at 100 ms.
    lag=anchors[-2]['shift']
    assert abs(lag-anchors[-1]['shift'])<=1 and min(v['correlation'] for v in anchors[-2:])>.995
    center=2400+50*48
    z=window(x,50,2048);before=window(y,50,2048);aligned=y[center-1024+lag:center+1024+lag]
    raw_fft=cents(hzfft(z),hzfft(before));reference_change=cents(hzfft(aligned),hzfft(before))
    held=cents(hzfft(z),hzfft(aligned));assert abs(raw_fft-held-reference_change)<1e-8
    return dict(recording=base,note_seconds=when,anchors=anchors,held_out_window_ms=[50-1024/48,50+1024/48],
        fixed_shift_samples=lag,fixed_shift_ms=lag/48,held_out_correlation=float(np.dot(z,aligned)/np.sqrt((z@z)*(aligned@aligned))),
        fft_hz=[hzfft(z),hzfft(before),hzfft(aligned)],fft_raw_cents=raw_fft,reference_window_change_cents=reference_change,fft_registered_cents=held,
        autocorrelation_raw_cents=cents(autocorr_hz(z),autocorr_hz(before)),
        autocorrelation_registered_cents=cents(autocorr_hz(z),autocorr_hz(aligned)))

def sensitivity():
    # A shift of the window must not remove a real detuning. Use the nominal F4 of the recording.
    f=440*2**(-4/12); t=np.arange(9600)/rate
    def tone(hz):
        return np.sin(2*np.pi*hz*t)+.24*np.sin(4*np.pi*hz*t+.3)
    def check(c):
        y=tone(f)[2400+272:2400+272+2048];x=tone(f*2**(c/1200))[2400:2400+2048]
        return [cents(fn(x),fn(y)) for fn in (hzfft,autocorr_hz)]
    controls=[{'injected':c,'estimated':check(c)} for c in [0.,-10.83]]
    assert all(abs(v-r['injected'])<.2 for r in controls for v in r['estimated'])
    return controls

if __name__=='__main__':
    fresh=sys.argv[1]
    result={'control':sensitivity(),'takes':[estimate(old,10),estimate(fresh,10),estimate(fresh,6)]}
    for r in result['takes']:
        print(r['note_seconds'],[round(float(r[k]),5) for k in ('fft_raw_cents','fixed_shift_ms','reference_window_change_cents','fft_registered_cents','autocorrelation_registered_cents','held_out_correlation')])
    print(result['control'])
    (root/'mtc-f4-splice-diagnosis.json').write_text(json.dumps(result,indent=2))
