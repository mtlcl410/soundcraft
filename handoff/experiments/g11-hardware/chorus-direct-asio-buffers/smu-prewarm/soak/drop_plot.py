from inspect_dips import *
from PIL import Image,ImageDraw,ImageFont
tag='long64';p=root/tag;b=read(p/'record.json')['buf'];events=read(root/('dips-'+tag+'.json'))
e=max(events,key=lambda v:v['quiet_samples'])
assert e['quiet_samples']==64
a=segment(load_wave(p/'out.bin'),e['out_frame']-128,448,b)@gain
h=segment(load_wave(p/'in.bin'),e['in_frame']-128,448,b)
im=Image.new('RGB',(1150,540),'#fbfbfa');s=ImageDraw.Draw(im)
def font(z,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),z)
s.text((40,23),'64 samples: a short level drop at the Model 12 MAIN return',font=font(28,True),fill='#182c37')
s.text((42,76),f"Playback {e['time_s']:.3f} s   |   64-sample comparison   |   1.451 ms at 44.1 kHz",font=font(19),fill='#394e55')
left,right=102,1095;peak=max(abs(a[:,0]).max(),abs(h[:,0]).max())
for track,(title,v,color) in enumerate([('ASIO 9/10 output, scaled to MAIN level',a,'#217184'),('Model 12 MAIN return, USB 11/12',h,'#62436d')]):
    top=155+track*159;bottom=top+101;mid=(top+bottom)/2
    def xx(i):return left+(right-left)*i/(len(v)-1)
    s.text((42,top-33),title,font=font(17,True),fill=color)
    s.rectangle((xx(128),top,xx(192),bottom),fill='#fae4bd')
    s.line((left,mid,right,mid),fill='#b3bbbf')
    s.line([(xx(i),mid-t/peak*48) for i,t in enumerate(v[:,0])],fill=color,width=2)
    s.text((left-8,mid),'0',anchor='rm',fill='#4e5d63',font=font(13))
for ms in range(-2,8):
    x=xx(128+ms*44.1)
    s.text((x,425),str(ms),anchor='mt',font=font(14),fill='#4e5d63')
s.text((595,461),'Milliseconds relative to the start of the measured dip',anchor='mt',font=font(17),fill='#4e5d63')
s.text((42,505),'Left channel shown. Stereo RMS in highlighted window: output %.1f, return %.2f (16-bit PCM counts).'%(e['pred_rms'],e['obs_rms']),font=font(16),fill='#4e5d63')
im.save(root/'main-dip-64.png')

