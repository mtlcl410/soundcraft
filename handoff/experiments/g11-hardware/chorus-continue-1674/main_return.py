from pathlib import Path
import os, time, sys, threading, json, wave
here=Path(__file__).resolve().parent
sys.path[:0]=[str(Path(os.environ["TEMP"])/"soundcraft-chorus-pa441"), str(here.parent/"capture-deps")]
os.environ["SD_ENABLE_ASIO"]="1"
import numpy as np
import pyaudiowpatch as pa
import sounddevice as sd
a=pa.PyAudio()
source=next(d for d in a.get_loopback_device_info_generator() if 'S/PDIF' in d['name'])
target=next(i for i,d in enumerate(sd.query_devices()) if d['name']=='Model Mixer ASIO')
buf=np.empty((0,2),'float32')
lock=threading.Lock()
ix=np.arange(441)*480/441
peak=0.; transfers=0; gaps=0; high=0
def capture(data,n,meta,flags):
    global buf,high
    x=np.frombuffer(data,'<f4').reshape(-1,2)
    y=np.column_stack([np.interp(ix,np.arange(n),ch) for ch in x.T]).astype('float32')
    with lock:
        buf=np.concatenate([buf,y])
        if len(buf)>3200:
            buf=buf[-1800:]
            high+=1
    return None,pa.paContinue
take=None
frames=[]
def save(name, chunks):
    if not chunks or not name:return
    with wave.open(str(here/(name+'-main.wav')),'wb') as w:
        w.setparams((2,2,44100,0,'NONE','')); w.writeframes(b''.join(c[1] for c in chunks))
    (here/(name+'-main-times.json')).write_text(json.dumps([c[0] for c in chunks]))
def render(inputs,out,n,t,flags):
    rx_time=time.perf_counter()+t.inputBufferAdcTime-t.currentTime
    if take:
        frames.append(([rx_time,n],(np.clip(inputs,-1.,.99996)*32768).astype('<i2').tobytes()))
    global buf,peak,transfers,gaps
    out.fill(0)
    with lock:
        k=min(n,len(buf))
        out[:k]=buf[:k]
        buf=buf[k:]
    if k<n: gaps+=1
    peak=max(peak,float(np.abs(out).max()))
    transfers+=k
def status():
    return dict(transferred=transfers,peak=peak,buffered=len(buf),short_callbacks=gaps,overflows=high)
stream=a.open(input=True,input_device_index=source['index'],rate=48000,channels=2,format=pa.paFloat32,frames_per_buffer=480,stream_callback=capture)
try:
    time.sleep(.035)
    with sd.Stream(device=(target,target),extra_settings=(sd.AsioSettings(channel_selectors=[10,11]),sd.AsioSettings(channel_selectors=[8,9])),samplerate=44100,channels=2,dtype='float32',callback=render):
        begin=time.monotonic()
        while time.monotonic()-begin<900 and not (here/'stop-monitor.flag').exists():
            time.sleep(.05)
            name=(here/'route-take.txt').read_text().strip() if (here/'route-take.txt').exists() else None
            if name!=take:
                prev=take; take=None
                old_frames=frames; frames=[]
                take=name
                save(prev,old_frames)
            tmp=here/'monitor-live.tmp'
            tmp.write_text(json.dumps(status()))
            tmp.replace(here/'monitor-live.json')
            if time.monotonic()-begin<.1: print("READY",status(),flush=True)
finally:
    stream.close()
    a.terminate()
