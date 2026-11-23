from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
w=Path(__file__).resolve().parent
rows=json.loads((w/'final-results.json').read_bytes());old=json.loads((w/'timing-native-128.json').read_bytes())
im=Image.new('RGB',(1100,520),'white');g=ImageDraw.Draw(im)
def font(px):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',px)
def label(x,y,text,size=20,fill='#24303b',anchor='la'):g.text((x,y),text,font=font(size),fill=fill,anchor=anchor)
label(45,24,'S-MU2000 first audio block',32)
label(45,79,'VST3 process time in milliseconds   |   Model 12 ASIO at 44.1 kHz',20)
for offset,size in enumerate((128,64)):
 x0=72+530*offset; base=405
 label(x0,121,f'{size} samples',25)
 axis=lambda t:base-t*21.5
 values=[old[f'native-{size}']['first_plugin_ms']]+[r['plugin_ms'] for r in rows if r['buffer']==size]
 for j,val in enumerate(values):
  x=x0+52+130*j
  g.rectangle((x-29,axis(val),x+29,base),fill='#647587' if j==0 else '#117d70')
  label(x,axis(val)-8,f'{val:.2f}',19,anchor='mb')
  label(x,base+13,['Installed','Warm 1','Warm 2'][j],18,anchor='ma')
 g.line((x0-8,base,x0+376,base),fill='#82929d',width=1)
 limit=old[f'native-{size}']['deadline_ms']; y=axis(limit)
 for xx in range(x0-8,x0+376,12):g.line((xx,y,xx+6,y),fill='#9a4e1f',width=2)
 label(x0,455,f'Dashed line: {limit:.3f} ms buffer budget',18,fill='#89451b')
im.save(w/'first-process.png')

