"""Plot host timestamps around source block 37504. USB rows show Model 12 UCX submissions."""
from pathlib import Path
import sys
import json

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[1]))
from timing import np
from PIL import Image,ImageDraw,ImageFont

r=json.loads((here/'results.json').read_bytes())['usb64r']
meta=json.loads((here.parent/'usb-evidence-usb64r.json').read_bytes())
ep={e['pipe']:e['address'] for e in meta['endpoints']}
im=Image.new('RGB',(1030,400),'white')
d=ImageDraw.Draw(im)
def label(x,y,t,size=17,bold=False):
    font=ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),size)
    d.text((x,y),t,font=font,fill='#203348')
def x(t):return 242+t*84
label(26,13,'ASIO and duplex USB timing at the 40-sample insertion',26,True)
label(26,53,'64 samples at 44.1 kHz  /  host timestamps relative to the PCM capture of output block #37504',17)
for tick in range(-1,9):
    d.line((x(tick),95,x(tick),313),fill='#e2e6ee')
    label(x(tick)-5,313,str(tick),15)
rows=[(118,'ASIO output PCM'),(170,'USB OUT submit'),(220,'USB IN submit'),(282,'MAIN input block')]
for y,t in rows:
    label(12,y-10,t,16,True)
    d.line((x(-.95),y,x(8),y),fill='#b2bfcb')
for e in r['callbacks']:
    t=e['output_ms']
    if -.95<t<=8:
        d.ellipse((x(t)-4,114,x(t)+4,122),fill='#255e9b')
for line in (here/'native-usb-usb64r.tsv').read_text().splitlines():
    stamp,kind,fields=line.split('\t',2)
    if kind!='200030':continue
    f=dict(w.split('=',1) for w in fields.split() if '=' in w)
    addr=ep.get(f['fid_PipeHandle'])
    t=(int(stamp)-r['source']['ns'])/1e6
    if addr in ('2','81') and -.95<t<=8:
        y=170 if addr=='2' else 220
        d.line((x(t),y-6,x(t),y+6),fill='#197563',width=3)
gap=r['usb']['OUT']['submit_gap']
for y,a,b,txt in [(118,0,3.5808,'3.581 ms'),(170,gap['start_ms'],gap['end_ms'],'2.020 ms')]:
    d.line((x(a),y-7,x(b),y-7),fill='#9f5600',width=2)
    label(x((a+b)/2)-30,y-33,txt,15)
t=r['main_witness_since_source_ms']
d.ellipse((x(t)-5,277,x(t)+5,287),fill='#8d3647')
label(x(t)-180,249,'#37509, samples 20–59',16)
label(242,346,'Elapsed milliseconds. The MAIN marker is when the input block was captured in software.',16)
im.save(here/'timing.png')
