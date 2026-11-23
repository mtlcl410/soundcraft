"""Plot the left channel of the measured splice with a common timing and level scale."""
from pathlib import Path
import runpy

here = Path(__file__).resolve().parent
s = runpy.run_path(str(here / 'overrun-splice.py'))
np = s['np']
from PIL import Image, ImageDraw, ImageFont

boundary = s['i']
pos = np.arange(-80, 145)
output = s['x'][boundary + pos, 0]
main = s['y'][boundary + pos, 0]
duration = s['post'] - s['pre']
im = Image.new('RGB', (1000, 485), 'white')
draw = ImageDraw.Draw(im)
def label(x, y, value, size=17, bold=False, color='#223449'):
    font = ImageFont.truetype('C:/Windows/Fonts/' + ('segoeuib.ttf' if bold else 'segoeui.ttf'), size)
    draw.text((x,y), value, fill=color, font=font)
def px(sample):
    return 98 + (sample + 80) * 3.76
limit = max(10, 5 * np.ceil(max(np.abs(output).max(), np.abs(main).max())/5))
label(35, 15, '40 extra samples in the Model 12 MAIN return', 28, True)
label(35, 58, '44.1 kHz  /  left channel  /  same scale, aligned before the insertion')
for level, name, signal, col in [(167, 'SoundCraft ASIO 9/10 output', output, '#185695'), (342, 'Model 12 MAIN return', main, '#08765f')]:
    label(35, level-78, name, 18, True, col)
    if signal is main:
        draw.rectangle((px(0), level-48, px(duration)-1, level+48), fill='#fce8bd')
        label(px(duration)+8, level-79, '0.907 ms', 18, True, '#915000')
    for v in [-limit, 0, limit]:
        yy = level - 48*v/limit
        draw.line((px(-80),yy,px(144),yy),fill='#e0e4e9')
        label(47,yy-12,str(int(v)),15)
    draw.line([(px(p),level-48*float(v)/limit) for p,v in zip(pos,signal)],fill=col,width=2)
    for v in (0,duration):
        draw.line((px(v),level-48,px(v),level+48),fill='#a48351')
for v in (-80,-40,0,40,80,120):
    label(px(v)-10,397,str(v),16)
label(102,432,'Samples from the start of output block #37504   /   amplitude in 16-bit PCM units')
im.save(here/'overrun-37504.png')
