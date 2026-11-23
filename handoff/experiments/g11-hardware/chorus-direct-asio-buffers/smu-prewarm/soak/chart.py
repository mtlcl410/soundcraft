from timing import *
from PIL import Image,ImageDraw,ImageFont
im=Image.new('RGB',(1250,685),'#fbfbfa');draw=ImageDraw.Draw(im)
def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),size)
draw.text((48,22),'Callback time during 10 minutes of continuous playback',font=font(33,True),fill='#172832')
draw.text((50,74),'Tallest measured callback in each second, as a percentage of the ASIO buffer duration',font=font(20),fill='#46545d')
panels=[]
for size in ('64','128'):
    p=root/('long'+size);j=read(p/'record.json');r=read(root/('timing-'+size+'.json'))['long']
    anchor=sum(j['anchors'])//2;t0=next(t for t,m in j['events'] if m==[248])+anchor
    stop=next(t for t,m in j['events'] if m==[252])+anchor
    a=load_profile(p/'profile.bin');a=a[(a[:,1]>=t0)&(a[:,1]<stop)]
    bins=np.minimum(599,((a[:,1].astype('int64')-t0)//10**9).astype(int))
    peaks=np.zeros(600);np.maximum.at(peaks,bins,a[:,2].astype(float)/1e6/r['deadline_ms']*100)
    panels.append((size,r,peaks))
top=max(125,int(np.ceil(max(v.max() for _,_,v in panels)/50))*50)
for k,(size,r,peaks) in enumerate(panels):
    left,right=113,1193;ystart=157+k*244;bottom=ystart+156
    def yy(v):return bottom-(bottom-ystart)*v/top
    draw.text((53,ystart-43),f"{size} samples    |    {r['deadline_ms']:.3f} ms budget    |    {r['all']['over']} over budget",font=font(19,True),fill='#172832')
    for tick in sorted(set([0,50,100,top])):
        ty=yy(tick)
        draw.line((left,ty,right,ty),fill='#bc6837' if tick==100 else '#cdd4d5',width=2 if tick==100 else 1)
        draw.text((left-9,ty),f'{tick}%',font=font(15),fill='#46545d',anchor='rm')
    pts=[(left+(right-left)*i/599,yy(float(v))) for i,v in enumerate(peaks)]
    draw.line(pts,fill='#27697b',width=2)
    for (x,y),v in zip(pts,peaks):
        if v>100:draw.ellipse((x-3,y-3,x+3,y+3),fill='#bc502b')
    for minute in range(11):
        x=left+(right-left)*minute/10
        draw.text((x,bottom+7),str(minute),font=font(15),fill='#46545d',anchor='mt')
draw.text((650,606),'Minutes after first MIDI Clock',font=font(18),fill='#46545d',anchor='mt')
draw.text((50,650),'SoundCraft / S-MU2000   •   Model 12 at 44.1 kHz   •   ASIO 9/10 to MAIN USB 11/12',font=font(16),fill='#53616a')
im.save(root/'callback-time.png')

