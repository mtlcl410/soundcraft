"""Independent input-only ASIO MAIN observer and DIN witness. No audio is forwarded."""
from pathlib import Path
import os,sys,json,time,threading,subprocess,wave
d=Path(__file__).resolve().parent
sys.path[:0]=[str(Path(os.environ['TEMP'])/'soundcraft-chorus-pa441'),str(d.parent),str(d.parent/'capture-deps')]
os.environ['SD_ENABLE_ASIO']='1'
import numpy as np, sounddevice as sd,rtmidi
from desktop_sync import cmd
p=json.loads((d/'control.json').read_text())['port']
takes=[('exact-a',64),('late-a',65),('exact-b',64),('exact-c',64),('late-b',65),('exact-d',64)]
def run():
 device=next(i for i,x in enumerate(sd.query_devices()) if x['name']=='Model Mixer ASIO')
 mi=rtmidi.MidiIn();ports=mi.get_ports();mi.ignore_types(sysex=True,timing=False,active_sense=True);mi.open_port(next(i for i,n in enumerate(ports) if n.startswith('UM-ONE')))
 midi=[];chunks=[];lock=threading.Lock()
 def incoming(ev,_):
    now=time.perf_counter()
    if ev[0] and ev[0][0] in (242,248,250,251,252):
        with lock:midi.append((now,list(ev[0])))
 mi.set_callback(incoming)
 def audio(ins,n,t,flags):
    q=time.perf_counter();m=[q,n,t.inputBufferAdcTime-t.currentTime,str(flags)]
    with lock:chunks.append((m,ins.copy()))
 try:
    with sd.InputStream(device=device,extra_settings=sd.AsioSettings(channel_selectors=[10,11]),samplerate=44100,channels=2,dtype='float32',blocksize=256,callback=audio):
      time.sleep(2)
      for name,spp in takes:
        assert not cmd(p,'transport.status')['playing']
        with lock:midi.clear();chunks.clear()
        time.sleep(.6)
        sub=subprocess.run([sys.executable,'exact_chorus.py',str(spp)],cwd=d,text=True,capture_output=True,timeout=12)
        if sub.returncode: raise RuntimeError(sub.stdout+sub.stderr)
        time.sleep(1.45)
        with lock: data=list(chunks);events=list(midi)
        assert len(data)>200,(name,len(data))
        with wave.open(str(d/(name+'.wav')),'wb') as w:
            w.setparams((2,2,44100,0,'NONE',''));w.writeframes((np.clip(np.concatenate([a for m,a in data]),-1,.99996)*32768).astype('<i2').tobytes())
        (d/(name+'.json')).write_text(json.dumps(dict(spp=spp,blocks=[m for m,a in data],midi=events,transport=cmd(p,'transport.status'),source=sub.stdout)))
        print(name,len(data),len(events),max(float(np.max(np.abs(a))) for m,a in data),flush=True)
 finally:mi.close_port()
if __name__=='__main__':run()

