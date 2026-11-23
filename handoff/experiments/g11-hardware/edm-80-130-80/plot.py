from pathlib import Path
from statistics import median
import json
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
out=root.parent.parent/'g11-storage-clock-follow/docs/images/midi-clock-edm-tempo.png'
image=Image.new('RGB',(1200,650),'white')
g=ImageDraw.Draw(image)
def txt(x,y,t,size,anchor='lm',bold=False):
    g.text((x,y),t,font=ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),size),anchor=anchor,fill='#172a38')
txt(38,42,'Timing across the two tempo changes',36,bold=True)
txt(38,90,'Follower hi-hat against the leader’s eighth-note grid (ms). Each line is one take.',23)
for panel,(change,title) in enumerate([(16,'80 → 130 BPM'),(32,'130 → 80 BPM')]):
    left=100+panel*575; right=left+466
    X=lambda i:left+i*(right-left)/8
    Y=lambda ms:312-ms*1.16
    txt((left+right)/2,151,title,28,'mm',True)
    for ms in (-120,-80,-40,0,40,80):
        y=Y(ms);g.line((left,y,right,y),fill=('#6b7881' if ms==0 else '#d9e1e4'))
        txt(left-12,y,str(ms),16,'rm')
    for i in range(9):
        txt(X(i),495,str(i),17,'mm')
    for path,col in [(root,'#bb725a'),(root/'final','#007b76')]:
        for n in range(1,4):
            j=json.loads((path/f'cal-{n}-result.json').read_bytes())
            pre=median(j['lag_ms'][change-8:change-1])
            points=[]
            for i in range(17):
                beat=change+i//2
                expected=(j['kick'][beat]+j['kick'][beat+i%2])/2
                diff=1000*(j['hat'][2*change+i]-expected)-pre
                points.append((X(i/2),Y(diff)))
            g.line(points,fill=col,width=3)
    txt((left+right)/2,536,'Beats since the tempo change',20,'mm')
for x,col,name in [(200,'#bb725a','Before'),(620,'#007b76','After')]:
    g.line((x,600,x+50,600),fill=col,width=4);txt(x+62,600,name,22)
image.save(out)
