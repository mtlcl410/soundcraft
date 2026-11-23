from analysis_audio import *
import os,time
os.environ['SD_ENABLE_ASIO']='1';sys.path.insert(0,str(Path(os.environ['TEMP'])/'soundcraft-chorus-pa441'))
import sounddevice as sd
from quality import quality
b=int(sys.argv[1]);keys=['repeat-128/exact-a'] if b==128 else ['repeat-64/exact-a','repeat-64/late-b','panel-64/exact-b']
dev=next(i for i,v in enumerate(sd.query_devices()) if v['name']=='Model Mixer ASIO')
summary=[]
for key in keys:
 p=src/key;dry=stereo(p.with_name(p.name+'-out.wav'));sig=(dry/32768).astype('float32');nmax=len(sig)+44100;cap=np.zeros((nmax+2048,2),'float32');pos=0;seen=set();flags=[]
 def cb(ins,out,n,t,flag):
    global pos
    seen.add(n);out.fill(0);cnt=max(0,min(n,len(sig)-pos))
    if cnt:out[:cnt]=sig[pos:pos+cnt]
    cnt=max(0,min(n,len(cap)-pos))
    if cnt:cap[pos:pos+cnt]=ins[:cnt]
    if flag:flags.append([pos,str(flag)])
    pos+=n
 with sd.Stream(device=(dev,dev),samplerate=rate,channels=2,dtype='float32',blocksize=0,extra_settings=(sd.AsioSettings(channel_selectors=[10,11]),sd.AsioSettings(channel_selectors=[8,9])),callback=cb):
    begin=time.monotonic()
    while pos<nmax and time.monotonic()-begin<12:time.sleep(.02)
 assert pos>=nmax and seen=={b},(pos,seen)
 y=np.rint(cap[:nmax]*32768);save(d/(key.replace('/','-')+'-replay.wav'),y)
 v=quality(dry,y);lag=v['lag_frames'];assert lag>=0
 clean=y[lag:lag+len(dry)]-dry@np.array(v['transfer']);v.update(key=key,buffer=b, flags=flags,peak_residual_step=float(abs(np.diff(clean,axis=0)).max()))
 summary.append(v);print(key,'step',v['peak_residual_step'],'drop',v['drop_windows'],flags,flush=True)
(d/f'replay-{b}.json').write_text(json.dumps(summary,indent=2))

