"""Calibrate only the final ASIO 9/10 to MAIN USB 11/12 leg at its observed level."""
import json, os, sys, time, wave
from pathlib import Path
here=Path(__file__).resolve().parent
sys.path[:0]=[str(Path(os.environ['TEMP'])/'soundcraft-chorus-pa441'),str(here.parent/'capture-deps')]
os.environ['SD_ENABLE_ASIO']='1'
import numpy as np
import sounddevice as sd
from assess import mono, matches
rate=44100
with wave.open(str(here.parent/'chorus-dispatch-release'/'boundary-b-asio-main.wav')) as f:
    assert f.getframerate()==rate and f.getnchannels()==2
    source=np.frombuffer(f.readframes(f.getnframes()),'<i2').reshape(-1,2).astype('float32')/32768
reference=mono(here/'Crash.wav')
tpl=np.interp(np.arange(184,2389)*48000/rate,np.arange(len(reference)),reference)
cor=matches(source.mean(1,dtype=np.float64)*32768,tpl)
assert .90<cor.max()<=1.000001
start=int(cor.argmax())-184
clip=source[start:start+4608].copy()
clip[-160:]*=np.linspace(1,0,160)[:,None]
offsets=[rate+round(rate*.62*i) for i in range(6)]
output=np.zeros((offsets[-1]+rate,2),'float32')
for i in offsets: output[i:i+len(clip)]=clip
pos=0; marks=[]; chunks=[]
def cb(ins,outs,n,t,flags):
    global pos
    stamp=time.perf_counter()
    outs.fill(0)
    k=min(n,max(0,len(output)-pos))
    if k:outs[:k]=output[pos:pos+k]
    chunks.append(ins.copy())
    marks.append([stamp,n,t.inputBufferAdcTime-t.currentTime,t.outputBufferDacTime-t.currentTime,str(flags)])
    pos+=n
device=next(i for i,d in enumerate(sd.query_devices()) if d['name']=='Model Mixer ASIO')
with sd.Stream(device=(device,device),extra_settings=(sd.AsioSettings(channel_selectors=[10,11]),sd.AsioSettings(channel_selectors=[8,9])),samplerate=rate,channels=2,dtype='float32',callback=cb):
    begin=time.monotonic()
    while pos<len(output):
        if time.monotonic()-begin>15: raise RuntimeError('ASIO callbacks timed out')
        time.sleep(.02)
audio=np.concatenate(chunks)
with wave.open(str(here/'asio-control-main.wav'),'wb') as f:
    f.setparams((2,2,rate,0,'NONE',''));f.writeframes((np.clip(audio,-1,.99996)*32768).astype('<i2').tobytes())
(here/'asio-control-blocks.json').write_text(json.dumps({'offsets':offsets,'blocks':marks}))
score=matches(audio.mean(1,dtype=np.float64)*32768,tpl);hits=np.flatnonzero(score>.9)
groups=np.split(hits,np.flatnonzero(np.diff(hits)>rate*.1)+1)
assert len(groups)==len(offsets),len(groups)
ends=np.cumsum([m[1] for m in marks])
def wall(fr,adc):
    i=int(ends.searchsorted(fr,side='right'));m=marks[i]
    return m[0]+(m[2] if adc else 0)+(fr-(ends[i]-m[1]))/rate
result=[]
for sent,g in zip(offsets,groups):
    ix=int(g[score[g].argmax()]);received=ix-184
    result.append(dict(callback_to_main_ms=round(1000*(wall(received,True)-wall(sent,False)),3),correlation=round(float(score[ix]),5),input_frame=received,output_frame=sent))

obj=dict(takes=result,flags=[m[4] for m in marks if m[4]],block_sizes=list(sorted(set(m[1] for m in marks))),rate=rate)
(here/'asio-control.json').write_text(json.dumps(obj,indent=2));print(obj)
