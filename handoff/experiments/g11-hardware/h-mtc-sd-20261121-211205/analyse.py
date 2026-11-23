from pathlib import Path
from collections import Counter
import json,sys,wave,math
ev=Path(__file__).resolve().parent
sys.path.insert(0,str(ev.parent/'capture-deps'))
import numpy as np
def pcm(file):
 with wave.open(str(file),'rb') as w:
  assert w.getnchannels()==1 and w.getsampwidth()==3 and w.getframerate()==48000,w.getparams()
  b=np.frombuffer(w.readframes(w.getnframes()),dtype=np.uint8).reshape(-1,3).astype(np.int32)
  return (((b[:,0] | (b[:,1]<<8) | (b[:,2]<<16))<<8)>>8)/8388608.
def db(val): return round(20*math.log10(max(float(val),1e-12)),2)
def analyse(file,expected_seconds):
 y=pcm(file)
 rate=48000
 exp=round(expected_seconds*rate)
 lo=max(0,exp-int(.42*rate))
 hi=min(len(y),exp+int(.42*rate))
 seg=y[lo:hi]
 if len(seg)<1440: raise ValueError('anchor outside WAV')
 env=np.sqrt(np.mean(seg[:len(seg)//48*48].reshape(-1,48)**2,axis=1))
 peak=float(env.max())
 if peak<1e-5: return {'detectable':False,'peak_dbfs':db(peak)}
 floor=float(np.median(env[:min(80,len(env)//5)]))
 threshold=max(peak*.05,floor*6)
 hits=np.flatnonzero((env[:-1]>threshold)&(env[1:]>threshold))
 if not len(hits): return {'detectable':False,'peak_dbfs':db(peak),'floor_dbfs':db(floor)}
 onset=lo+int(hits[0])*48+24
 win=y[onset+480:onset+480+4096]
 sp=abs(np.fft.rfft(win*np.hanning(len(win)),65536))
 bins=np.fft.rfftfreq(65536,1/rate)
 def band(f):
  mask=(bins>f-12)&(bins<f+12)
  return float(bins[mask][sp[mask].argmax()]),float(sp[mask].max())
 a4=band(440);c4=band(261.63)
 return dict(detectable=True,expected_wave_seconds=expected_seconds,onset_wave_seconds=onset/rate,signed_offset_ms=round((onset-exp)*1000/rate,3),peak_dbfs=db(peak),floor_dbfs=db(floor),a4_band_hz=round(a4[0],2),a4_over_c4_db=db(a4[1]/max(c4[1],1e-14)),envelope_window_ms=1)
if __name__=='__main__':
 label,ch1,ch2,expected=sys.argv[1:]
 a,b=Path(ch1),Path(ch2)
 result=dict(marker='A4',ch1_peak_dbfs=db(abs(pcm(a)).max()),ch1_rms_dbfs=db(np.sqrt(np.mean(pcm(a)**2))),ch2_peak_dbfs=db(abs(pcm(b)).max()),ch2_seconds=len(pcm(b))/48000,anchor=analyse(b,float(expected)))
 print(json.dumps(result,indent=2))
 (ev/(label+'-audio.json')).write_text(json.dumps(result,indent=2))
