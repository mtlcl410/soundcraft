"""Independent ten-minute oscillator calibration vs observed, held-out physical wire counts."""
import json
from pathlib import Path
from itertools import accumulate
from reportlab.graphics.shapes import Drawing,String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor

a=Path(__file__).resolve().parent
p=a/'dedicated-source-two-hours'
rows=json.loads((p/'counter-domains.json').read_text())['windows']
scale=rows[0]['effective_hz']/48_000.-1
held=rows[1:]
x=[0,*accumulate(r['wall_s']/60 for r in held)]
fig=Drawing(630,430)
def label(x,y,value,size=10,color='#25323a'):
    fig.add(String(x,y,value,fontName='Helvetica',fontSize=size,fillColor=HexColor(color)))
label(42,407,'Held-out DIN output against a 10-minute ASIO calibration',18)
label(42,387,'Model 12, 48 kHz / 256 samples. Steady external 120 BPM.',11)
for bottom,caption,key,rate in [(225,'Beat Clock','f8_excess',48),(54,'MTC quarter-frames','qf_excess',120)]:
    predicted=[t*60*scale*rate for t in x]
    measured=[0,*accumulate(r[key] for r in held)]
    plot=LinePlot();plot.x=62;plot.y=bottom;plot.width=475;plot.height=108
    plot.data=[list(zip(x,measured)),list(zip(x,predicted))]
    plot.xValueAxis.valueMin=0;plot.xValueAxis.valueMax=100;plot.xValueAxis.valueStep=20
    plot.yValueAxis.valueMin=0;plot.yValueAxis.valueMax=(15 if rate==48 else 30);plot.yValueAxis.valueStep=5
    plot.lines[0].strokeColor=HexColor('#026b74');plot.lines[0].strokeWidth=2.5
    plot.lines[1].strokeColor=HexColor('#aa451e');plot.lines[1].strokeWidth=1.5;plot.lines[1].strokeDashArray=[5,3]
    fig.add(plot);label(42,bottom+122,caption+' / cumulative excess messages',12)
    label(548,bottom+75,f'{measured[-1]:g} actual',10,'#026b74')
    label(548,bottom+59,f'{predicted[-1]:.2f} model',10,'#aa451e')
label(140,15,'Minutes after calibration (transport boundaries excluded)')
renderSVG.drawToFile(fig,str(a/'clock-domains-held-out.svg'))
