"""Plot the longest measured outside-work gap per buffer on one common time scale."""
from pathlib import Path
import sys,json,math
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from timing import *
from PIL import Image,ImageDraw,ImageFont
im=Image.new('RGB',(1360,710),'#faf9f6');draw=ImageDraw.Draw(im)
def label(x,y,text,n=20,bold=False,col='#172b34'):
 f=ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),n);draw.text((x,y),text,font=f,fill=col)
items=[]
for tag in ('usb64r','usb128'):
 g=read(Path(f'gaps-{tag}.json'))['rows'][0];s=read(Path(f'stages-{tag}.json'))[0];e=read(Path(f'usb-evidence-{tag}.json'))
 pipes={x['pipe'] for x in e['endpoints'] if x['address'] and int(x['address'],16)<128 and x['attributes'] and int(x['attributes'],16)&3==1}
 assert pipes
 times=[]
 for line in Path(f'native-usb-{tag}.tsv').open():
  ts,k,d=line.rstrip('\r\n').split('\t',2);t=int(ts)
  if k=='200031' and any('fid_PipeHandle='+pipe+' ' in d+' ' for pipe in pipes):
   rel=(t-g[1])/1e6
   if -.5<=rel<=g[3]+.5:times.append(rel)
 items.append((tag,g,s,times))
left,right=245,1290;end=math.ceil(max(x[1][3] for x in items)+.5);origin=-.5
def x(t):return left+round((t-origin)/(end-origin)*(right-left))
label(42,22,'Inside the longest ASIO callback gap',34,True)
label(43,75,'Model 12 ASIO 9/10 at 44.1 kHz     |     Independent 9-minute plays     |     Time is relative to the previous work ending',20)
palette={'Wait':'#386b98','Ready':'#d58719','Run':'#198070','Unknown':'#a3a4a4'}
for row,(tag,g,s,times) in enumerate(items):
 y=136+row*245
 label(43,y,('64' if row==0 else '128')+' samples',25,True)
 label(246,y,f'Gap {g[3]:.3f} ms   ·   Previous callback #{g[0]:,}',23,True)
 y+=59
 for i in range(end+1):
  draw.line((x(i),y-6,x(i),y+91),fill='#d4d9d8');label(x(i)-4,y+95,str(i),15)
 label(43,y+3,'ASIO thread',18);label(43,y+56,'USB OUT complete',18)
 trans=s['transitions'];state=s.get('initial_state','Run' if (trans and trans[0]['state']=='Wait') else 'Wait');t=0
 for v in trans+[{'at_ms':g[3],'state':None}]:
  stop=min(g[3],max(t,v['at_ms']))
  if stop>t:draw.rectangle((x(t),y,x(stop),y+30),fill=palette[state])
  t=stop;state=v['state']
 for tick in times:
  draw.line((x(tick),y+52,x(tick),y+84),fill='#8e4562',width=3)
 for tick in (0,g[3]):draw.line((x(tick),y-6,x(tick),y+38),fill='#192a33',width=2)
 label(right-18,y+112,'ms',15)
for i,(title,key) in enumerate([('Waiting for a signal','Wait'),('Ready for CPU','Ready'),('Scheduled on CPU','Run')]):
 xx=45+i*335;draw.rectangle((xx,639,xx+21,654),fill=palette[key]);label(xx+30,631,title,18)
label(45,671,'USB marks are host-reported transfer completions on the Model 12 playback endpoint.',18)
im.save('callback-and-usb.png')

