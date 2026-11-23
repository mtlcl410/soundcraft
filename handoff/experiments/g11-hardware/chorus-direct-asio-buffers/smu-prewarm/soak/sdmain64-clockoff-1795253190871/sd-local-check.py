from pathlib import Path
import sys,json,numpy as np
case=Path(sys.argv[1]).resolve();E={'__file__':str(case/'sd-landmarks.py')}
exec(compile((case/'sd-landmarks.py').read_text(encoding='utf-8-sig').split('res={}')[0],E['__file__'],'exec'),E)
fetch,out,usb,wav,best=(E[k] for k in ('fetch','out','usb','wav','best'))
from audio import gain
four=json.loads((case/'four-paths.json').read_bytes());changes=json.loads((case/'transition-fit.json').read_bytes())
rows=[];controls=[]
def power(x):return float(np.sqrt(np.mean(np.square(np.asarray(x,dtype=float)))))
for i in (0,1):
 sd=wav(11+i);ana=wav(3+i)
 for j,(z,route) in enumerate(zip(changes,four['paths'][i]['offset_changes'])):
  if z['delta']<=0:continue
  gap=z['delta'];u=z['usb_frame'];s=u+route['before']['sd_minus_usb']
  a=s+route['before']['sd_analog_minus_internal']
  for name,v,idx in [('internal',sd,s),('analog',ana,a)]:
   y=v[idx-64:idx+gap+64]*32768
   rows.append(dict(ch=i+1,sec=z['seconds'],route=name,step=gap,rms_before=power(y[:64]),rms_inside=power(y[64:-64]),rms_after=power(y[-64:])))
 # Use the captured low-level old passage itself as reference for an unchanged
 # control and for a known insert in a COPY of each SD track.
 hist=four['paths'][i]['target'][0];pos=four['historical_source_matches'][-1]['frame']+hist['usb_minus_out']+hist['sd_minus_usb']
 for name,v,idx in [('internal',sd,pos),('analog',ana,pos+hist['sd_analog_minus_internal'])]:
  r=v[idx-1200:idx+1200]
  noise=v[4000:4040];synthetic=np.r_[r[:1200],noise,r[1200:]]
  for key,y in [('unchanged',r),('inserted',synthetic)]:
   lag=[]
   for begin in (240,1500):
    k,_=best(y,r[begin:begin+512],begin,64);lag.append(k-begin)
   controls.append(dict(channel=i+1,path=name,case=key,recovered=lag[1]-lag[0]))
   assert lag[1]-lag[0]==(40 if key=='inserted' else 0)
(case/'transition-sd-rms.json').write_text(json.dumps(dict(unit='16-bit equivalent PCM',events=rows,sensitivity=controls),indent=2))
for r in rows:print(r)

