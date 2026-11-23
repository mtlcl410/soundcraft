import json,wave,sys,pathlib,statistics
here=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/'capture-deps'))
import numpy as np
def mono(f):
 with wave.open(str(f)) as w:
  return np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float).reshape(-1,w.getnchannels()).mean(1)
def matches(audio,needle):
 size=1<<(len(audio)+len(needle)-1).bit_length()
 corr=np.fft.irfft(np.fft.rfft(audio,size)*np.fft.rfft(needle[::-1],size),size)[len(needle)-1:len(audio)]
 e=np.r_[0,np.cumsum(audio**2)];energy=np.maximum(e[len(needle):]-e[:-len(needle)],1)
 return corr/np.sqrt(energy*(needle@needle))
def measure(mode):
 j=json.loads((here/(mode+'.json')).read_text());x=mono(here/(mode+'.wav'));rate=j['rate'];b=j['blocks']
 if not len(x):return {'mode':mode,'captured_frames':0}
 limits=np.cumsum([v[1] for v in b])
 def wall(frame):
  i=min(int(limits.searchsorted(frame,side='right')),len(b)-1)
  return b[i][0]-(limits[i]-frame)/rate
 s=matches(x,mono(here/'Crash.wav')[200:2600]);best=int(s.argmax())
 # One independent match per 100 ms, including candidates after Stop.
 hits=np.flatnonzero(s>.90);groups=np.split(hits,np.flatnonzero(np.diff(hits)>rate*.1)+1) if len(hits) else []
 frames=[int(g[s[g].argmax()])-200 for g in groups]
 when=j['begin']
 result=dict(mode=mode,frames=len(x),host_start=when,host_stop=j['end'],crash_count=len(frames),best_crash_match=round(float(s[best]),5),crash_recording_frames=frames)
 results={}
 for source in sorted(set(v[1] for v in j['midi'])):
  data=[(t,m) for t,n,m in j['midi'] if n==source];controls=[(t,m) for t,m in data if m[0]!=248]
  starts=[(t,m) for t,m in controls if m[0] in (250,251)]
  if not starts:continue
  t,cmd=starts[-1];loc=[m[1]+128*m[2] for ts,m in controls if ts<=t and m[0]==242]
  stop=next((tt for tt,m in controls if tt>t and m[0]==252),None);ticks=[tt for tt,m in data if tt>=t and (stop is None or tt<stop) and m[0]==248]
  target_tick=384 if cmd[0]==250 else (64-loc[-1])*6 if loc else None
  expected=ticks[target_tick] if target_tick is not None and 0<=target_tick<len(ticks) else None
  after=next((v for ts,v,f in reversed(j['states']) if ts<=t and not v['playing']),None)
  audible=np.flatnonzero(abs(x)>24)
  results[source]=dict(transport='Start' if cmd[0]==250 else 'Continue',preceding_spp=loc,stopped_position=after,clock_count=len(ticks),bpm=round(60/(np.median(np.diff(ticks))*24),3) if len(ticks)>5 else None,stop=stop,crash_vs_wire_ms=[round((wall(fr)-expected)*1000,2) for fr in frames] if expected is not None else None,first_audible_vs_crash_ms=round((frames[0]-audible[0])*1000/rate,2) if frames and len(audible) else None)
 result['wire']=results
 (here/(mode+'-analysis.json')).write_text(json.dumps(result,indent=2))
 return result
if __name__=='__main__':print(json.dumps(measure(sys.argv[1]),indent=2))
