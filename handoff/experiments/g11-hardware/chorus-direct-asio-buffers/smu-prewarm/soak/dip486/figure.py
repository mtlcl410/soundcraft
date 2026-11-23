from original import *
from PIL import Image,ImageDraw,ImageFont
r=read(here/'original.json')[0];f=r['output_frame'];g=r['input_frame'];p=root/'long64'
left=-210;right=220
xx=segment(load_wave(p/'out.bin'),f+left,right-left+107,64)@gain
yy=segment(load_wave(p/'in.bin'),g+left,right-left,64)
im=Image.new('RGB',(1200,668),'#fafaf8');draw=ImageDraw.Draw(im)
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def label(x,y,t,n=17,color='#26373e',bold=False):draw.text((x,y),t,font=font(n,bold),fill=color)
label(43,20,'Model 12 MAIN  |  486.242 s, 64 samples at 44.1 kHz',32,bold=True)
label(45,74,'The 107-sample near-silent interval separates two adjacent samples of the ASIO output.',21)
X=lambda k:90+(k-left)/(right-left)*1050
top,bottom=150,342;mid=(top+bottom)/2;scale=88/(abs(yy[:,0]).max())
draw.rectangle((X(-43),top,X(64),bottom),fill='#fce5b6')
draw.line((X(left),mid,X(right),mid),fill='#acb6bb')
draw.line([(X(k),mid-yy[k-left,0]*scale) for k in range(left,right)],fill='#8b3b54',width=3)
for ran,shift in [(range(left,-43),107),(range(64,right),0)]:
    draw.line([(X(k),mid-xx[k-left+shift,0]*scale) for k in ran],fill='#178192',width=1)
label(90,111,'MAIN return (left channel)',16,'#8b3b54',True)
label(355,111,'ASIO output, aligned on each side',16,'#178192',True)
label(X(-43)+9,154,'2.43 ms',19,'#654311',True)
label(91,349,'Sample-matched stereo RMS error after joining the two flanks: 0.95 PCM counts.',17)
label(46,414,'Time between two successive SoundCraft processing starts',23,bold=True)
start,end=90,1138;w=(end-start)/7.0
for t0,t1,c in [(0,.4193,'#178192'),(.4193,6.5181,'#ddd5bd'),(6.5181,6.918,'#178192')]:
    draw.rectangle((start+t0*w,470,start+t1*w,500),fill=c)
for i in range(8):
    x=start+i*w;draw.line((x,501,x,507),fill='#777');label(x-3,511,str(i),15)
label(start+1,550,'0.419 ms work',17,'#176977',True)
label(438,550,'6.099 ms between measured blocks',18,'#615332',True)
label(945,550,'0.400 ms work',17,'#176977',True)
label(46,616,'Upper panel: recorded samples. Lower panel: wall time (ms); the two panels have independent origins.',16)
im.save(here/'main-gap-and-callback.png')

