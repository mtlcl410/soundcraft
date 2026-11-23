from pathlib import Path
import sys,json
case=Path(sys.argv[1])
s=(case/'sd-landmarks.py').read_text(encoding='utf-8-sig')
exec(compile(s.split('res={}')[0],str(case/'sd-landmarks.py'),'exec'),(env:={'__file__':str(case/'sd-landmarks.py')}))
np=env['np']; fetch=env['fetch']; best=env['best']
out,usb=env['out'],env['usb']
rows=[]
for sec in (13.45,13.47,13.50,13.52):
 off=round(sec*44100);span=1800
 for c in (0,1):
  ref=fetch(out,off,1024)[:,c]; y=fetch(usb,off-span,1024+2*span)[:,c]
  k,sc=best(y,ref,span,span);rows.append(dict(time=sec,ch=c,lag_in_own_start_frames=k-span,corr=sc))
print(rows)
(case/'target-output-usb.json').write_text(json.dumps(rows,indent=2))
j=json.load(open(case/'sd-landmarks.json'))
for c,v in j.items():
 print('ch',c,'offsets',sorted(set(q['sd_minus_usb'] for a in v['landmarks'] for q in a['checks'])),'analog',sorted(set(q['analog_minus_sd'] for a in v['landmarks'] for q in a['checks'])))
