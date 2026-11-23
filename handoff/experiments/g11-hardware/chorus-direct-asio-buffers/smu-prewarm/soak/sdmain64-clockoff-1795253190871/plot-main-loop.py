from pathlib import Path
import sys,json,numpy as np
from PIL import Image,ImageFont,ImageDraw
size=(1440,780)
im=Image.new('RGB',size,'white');dr=ImageDraw.Draw(im)
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def label(x,y,v,n=18,color='#27374b',bold=False):dr.text((x,y),v,fill=color,font=font(n,bold))
label(38,21,'Model 12 MAIN output during MIDI Clock follow',34,bold=True)
label(38,77,'Three recorded paths are aligned to the source waveform. The shaded interval marks the fitted insertion.',21)
for panel,arg in enumerate(sys.argv[1:3]):
 case=Path(arg).resolve(); E={'__file__':str(case/'sd-landmarks.py')}
 exec(compile((case/'sd-landmarks.py').read_text(encoding='utf-8-sig').split('res={}')[0],E['__file__'],'exec'),E)
 buf=E['buf']; events=json.loads((case/'transition-fit.json').read_bytes())
 i=next(i for i,e in enumerate(events) if e['delta']==(27 if buf==64 else 22));e=events[i]
 route=json.loads((case/'four-paths.json').read_bytes())['paths'][0]['offset_changes'][i]['before']
 output=e['out_frame'];u=e['usb_frame']; delta=e['delta']; s=u+route['sd_minus_usb'];p=s+route['sd_analog_minus_internal']
 l,r=70,80+delta
 fetch=E['fetch'];n=l+r+1
 paths=[fetch(E['out'],output-l,n)[:,0],fetch(E['usb'],u-l,n)[:,0]]
 for ch,ctr in [(11,s),(3,p)]:
  with E['wave'].open(str(next(E['src'].glob('*TR%02d.wav'%ch))),'rb') as w:
   w.setpos(ctr-l);bits=np.frombuffer(w.readframes(n),dtype=np.uint8).reshape(-1,3)
   v=(bits[:,2].astype(np.int8).astype(np.int32)<<16)+(bits[:,1].astype(np.int32)<<8)+bits[:,0]
   paths.append(v/8388608)
 base=44+panel*710;x0=base+136;edge=base+655
 def x(k):return x0+((k+l)/(n-1))*(edge-x0)
 label(base,133,f'{buf} samples',25,bold=True)
 label(base,175,f'{e["seconds"]:.3f} s    |    +{delta} samples ({delta/44.1:.3f} ms)',19)
 for row,(name,wv,color) in enumerate(zip(['ASIO out 9','USB MAIN L','SD MAIN L','SD CH3 line'],paths,['#1e426d','#146e79','#744697','#9b5615'])):
  y=272+row*115; label(base,y-14,name,18)
  dr.rectangle((x(0),y-41,x(delta),y+41),fill='#f8e6bf')
  dr.line((x0,y,edge,y),fill='#bed1d7')
  scale=35/max(abs(wv)); dr.line([(x(k-l),y-float(v)*scale) for k,v in enumerate(wv)],fill=color,width=2)
 for k in [-60,0,delta,80]:
  dr.line((x(k),663,x(k),672),fill='#526373');label(x(k)-9,675,str(k),17)
 label(base+160,706,'Samples from fitted boundary',17)
label(40,746,'Left channel shown. Each trace has its own vertical scale. Horizontal offsets include the calibrated analog-loop delay.',16)
im.save(sys.argv[3])


