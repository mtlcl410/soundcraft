from pathlib import Path
import json,wave,sys
d=Path(__file__).resolve().parent;sys.path.insert(0,str(d.parent/'capture-deps'))
import numpy as np
def stereo(path):
 with wave.open(str(path)) as w:
    assert w.getframerate()==44100 and w.getnchannels()==2
    return np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float).reshape(-1,2)
def quality(x,y):
 # Lock a single delay for the whole take. Re-aligning every block could hide dropped/repeated samples.
 a=x.mean(1);b=y.mean(1);length=1<<(len(a)+len(b)-1).bit_length()
 corr=np.fft.irfft(np.fft.rfft(a[::-1],length)*np.fft.rfft(b,length),length)
 lag=int(np.argmax(corr))-len(a)+1
 assert abs(lag)<44100//4,lag
 x=x[max(0,-lag):];y=y[max(0,lag):];n=min(len(x),len(y));x=x[:n];y=y[:n]
 # MAIN level/pan may differ. Fit the stereo mix once, then compare every sample.
 active=np.max(abs(x),axis=1)>50
 gain=np.linalg.lstsq(x[active],y[active],rcond=None)[0];pred=x@gain;err=y-pred
 win=64;N=n//win*win
 def rms(v):return np.sqrt((v[:N]**2).reshape(-1,win,2).mean(axis=(1,2)))
 sig=rms(pred);res=rms(err);obs=rms(y);amp=np.max(abs(err),axis=1)
 # Floors in 16-bit PCM counts keep room/ADC noise from flagging silent passages.
 bad=np.flatnonzero((res>8)&(res>.16*sig));drops=np.flatnonzero((sig>30)&(obs<.2*sig))
 return dict(lag_frames=lag,transfer=gain.tolist(),peak_residual_counts=float(amp.max()),max_window_residual=float(res.max()),bad_windows=len(bad),drop_windows=len(drops),impulse_samples=int(np.sum(amp>64)),main_peak_counts=float(np.max(abs(y))),bad_window_times=(bad*win/44100).round(4).tolist()[:12])
if __name__=='__main__':
 for f in (d/sys.argv[1]).glob('*-out.wav'):
    z=quality(stereo(f),stereo(f.with_name(f.name.replace('-out','-in'))))
    print(f.name,{k:v for k,v in z.items() if k!='transfer'})

