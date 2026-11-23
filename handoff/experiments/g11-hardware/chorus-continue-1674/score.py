from assess import mono,matches,here
import json,numpy as np,wave
def read(name):
 return json.loads((here/name).read_text())
ref=mono(here/'monitor-reference.wav')
cr=read('monitor-reference-analysis.json')['crash_recording_frames'][0]
needle=mono(here/'Crash.wav'); rate=44100
# Use the same physical MAIN return for the pattern once the known reference is located.
def locate(x,n):
 s=matches(x,n); k=int(s.argmax())
 hits=np.flatnonzero(s>.90); groups=np.split(hits,np.flatnonzero(np.diff(hits)>rate*.1)+1) if len(hits) else []
 return float(s[k]),[int(g[s[g].argmax()]) for g in groups]
mainref=mono(here/'monitor-reference-main.wav')
r=np.arange(0,2600*rate/48000)*48000/rate
resamp=np.interp(r,np.arange(len(needle)),needle)
peak,refs=locate(mainref,resamp[184:2200]);print('reference MAIN',peak,refs)
out={}
for mode in ['monitor-reference','boundary-a','later-a','boundary-b','later-b','one-beat']:
 a=read(mode+'-analysis.json');j=read(mode+'.json');m=mono(here/(mode+'-main.wav'))
 din=next((z for z in a['wire'] if z.startswith('UM-ONE')),None)
 z=a['wire'].get(din,{})
 score,mainhits=locate(m,resamp[184:2200]);d=dict(digital_count=a['crash_count'],digital_match=a['best_crash_match'],wire_ms=z.get('crash_vs_wire_ms'),spp=z.get('preceding_spp'),first_sound_ms=z.get('first_audible_vs_crash_ms'),clocks=z.get('clock_count'),main_match=round(score,5),main_source_matches=len(mainhits),main_peak=int(abs(m).max()))
 if refs:
  score2,mm=locate(m,mainref[refs[0]:refs[0]+2000]);d.update(main_reference_score=round(score2,5),main_count=len(mm))
  ticks=[t for t,n,msg in j['midi'] if n==din and msg[0]==248]
  if ticks and mm and z.get('preceding_spp') and z['preceding_spp'][-1]<=64:
   tick=ticks[(64-z['preceding_spp'][-1])*6]
   seq=read(mode+'-main-times.json'); ends=np.cumsum([n for ts,n in seq]); deltas=[]
   for hit in mm:
    onset=hit-184;i=int(ends.searchsorted(onset,side='right'));time=seq[i][0]+(onset-(ends[i]-seq[i][1]))/rate
    deltas.append(round(1000*(time-tick),2))
   d['main_wire_ms']=deltas
 if mode!='monitor-reference':
  x=mono(here/(mode+'.wav'));tpl=ref[cr+24000:cr+26000]
  d['later_music_match']=round(float(np.max(matches(x,tpl))),5)
 out[mode]=d
print(json.dumps(out,indent=2));(here/'results.json').write_text(json.dumps(out,indent=2))
