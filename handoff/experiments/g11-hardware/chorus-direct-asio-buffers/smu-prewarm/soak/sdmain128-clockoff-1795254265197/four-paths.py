"""Compare the historical splice and observed offset transitions using four live witnesses."""
from pathlib import Path
import sys,json
import numpy as np
case=Path(sys.argv[1]).resolve()
env={'__file__':str(case/'sd-landmarks.py')}
src=(case/'sd-landmarks.py').read_text(encoding='utf-8-sig')
exec(compile(src.split('res={}')[0],env['__file__'],'exec'),env)
fetch,best,out,usb,wav,load_wave=(env[k] for k in ('fetch','best','out','usb','wav','load_wave'))
R=44100
blocks=env['buf']
audio=json.loads((case.parent/('audio-'+case.name+'.json')).read_bytes())
land=json.loads((case/'sd-landmarks.json').read_bytes())
# The old affected source callback was already located by sample, at offset zero.
old=json.loads((case.parent/'etw-gap/splice-usb/results.json').read_bytes())['usb64r']['source']
oldw=load_wave(case.parent/'usb64r/out.bin')
oldpos=int(np.searchsorted(oldw['serial'],old['serial']))*64 + old['offset']
def clip64(a,x,n):
 k,b=divmod(x,64)
 return a[k:k+(b+n+63)//64]['samples'][:,:64].reshape(-1,2)[b:b+n]
lo=round(13.498*R)-9000
pool=fetch(out,lo,18000).mean(1)
def match_old(delta,n):
 ref=clip64(oldw,oldpos+delta,n).mean(1)
 sc=env['corr_scores'](pool,ref)
 k=int(sc.argmax())
 return {'frame':int(lo+k-delta),'score':float(sc[k])}
refs=[match_old(-1200,1024),match_old(192,1024),match_old(-1500,3000)]
f=refs[-1]['frame']
changes=[(i,c['time_s']) for i,c in enumerate(audio['chunks']) if i>0 and c['lag']!=audio['chunks'][i-1]['lag']]
rows=[]
for ch in (0,1):
 digital=wav(11+ch);analog=wav(3+ch)
 base=land[str(ch)]['base']
 def measure(pos,n):
  r=fetch(out,pos,n)[:,ch]
  width=1800;u=fetch(usb,pos-width,n+2*width)[:,ch]
  k,sc=best(u,r,width,width)
  up=pos-width+k
  sy,ds=best(digital,fetch(usb,up,n)[:,ch],base+up,240)
  ay,ascore=best(analog,digital[sy:sy+n],sy+38,60)
  return {'out_frame':pos,'usb_minus_out':up-pos,'sd_minus_usb':sy-up,'sd_analog_minus_internal':ay-sy,
          'sd_minus_out_less_base':sy-pos-base,'analog_minus_out_less_base':ay-pos-base,
          'correlations':[sc,ds,ascore]}
 anchors=[measure(f-1280,1024),measure(f+192,1024)]
 targets=[]
 for i,sec in changes:
  if sec<2.0 or sec>537.0:continue
  def reliable(sign):
   attempts=[measure(round((sec+sign*k)*R),2048) for k in (1.2,1.4,1.6,1.8,2.)]
   return max(attempts,key=lambda q:min(q['correlations']))
  a=reliable(-1);b=reliable(1)
  targets.append(dict(sec=sec,before=a,after=b,delta={k:b[k]-a[k] for k in ('usb_minus_out','sd_minus_usb','sd_minus_out_less_base','analog_minus_out_less_base')}))
 rows.append({'channel':ch,'target':anchors,'offset_changes':targets})
(case/'four-paths.json').write_text(json.dumps(dict(historical_source_matches=refs,paths=rows),indent=2))
print('source',refs,'target', [[(w['usb_minus_out'],w['sd_minus_usb'],w['sd_analog_minus_internal']) for w in v['target']] for v in rows])
for r in rows[:1]:
 for v in r['offset_changes']: print(round(v['sec'],2),v['delta'])

