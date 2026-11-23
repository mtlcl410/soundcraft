from desktop_sync import *
desktop=sys.argv[2] if len(sys.argv)>2 else 'mtc-phase'
p=json.loads((root/(desktop+'-control.json')).read_text())['port']
sys.path.insert(0,str(root/'capture-deps'))
def c(action,**kv):
    return cmd(p,action,**kv)
import pyaudiowpatch as pa, wave, threading
from collections import deque
ap=pa.PyAudio()
name=c('ui.audio_device')['device']['name']+' [Loopback]'
dev=next(d for d in ap.get_loopback_device_info_generator() if d['name']==name)
rate=int(dev['defaultSampleRate'])
channels=dev['maxInputChannels']
blocks=deque(maxlen=80)
saved=[]
retain=False
lock=threading.Lock()
def recv(data,n,meta,flags):
    now=time.perf_counter()
    with lock:
        item=(now,n,data,int(flags))
        blocks.append(item)
        if retain: saved.append(item)
    return None,pa.paContinue
stream=ap.open(format=pa.paInt16,channels=channels,rate=rate,input=True,input_device_index=dev['index'],frames_per_buffer=480,stream_callback=recv)
run=sys.argv[1]
base='smu-phase-'+run+'-'+str(time.time_ns())
import subprocess, tempfile, struct, pathlib
started=ended=None
offset=time.time_ns()-time.perf_counter_ns()
scratch=tempfile.TemporaryDirectory()
raw=pathlib.Path(scratch.name)/'endpoint.bin'
native=subprocess.Popen([str(root/'phase-loopback.exe'),str(raw)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
msg=native.stdout.readline()
if b'READY' not in msg: raise RuntimeError(str(msg)+str(native.communicate()))
states=[]
import rtmidi
from collections import Counter
ports=[]
messages=[]
def on_midi(ev,n):
    if ev[0] and ev[0][0] in (241,240,252): messages.append([time.perf_counter(),n,ev[0]])
for i,n in enumerate(rtmidi.MidiIn().get_ports()):
    if n.startswith(('Model 12 MIDI ','UM-ONE ')):
        m=rtmidi.MidiIn();m.ignore_types(sysex=False,timing=False,active_sense=True)
        try:
            m.open_port(i);m.set_callback(on_midi,n);ports.append(m)
        except Exception as e: print(e,flush=True)
try:
    if run=='live':
        print(c('setup.mtc',input='UM-ONE',online=True),flush=True)
    else:
        c('transport.locate',at=240000)
    time.sleep(.4)
    print('ARMED',base,c('transport.status'),flush=True)
    if run=='reference': c('transport.play',**{'from':240000})
    t=time.perf_counter()
    started=None
    ended=None
    while time.perf_counter()-t<900:
        now=time.perf_counter()
        chase=c('setup.mtc')
        trans=c('transport.status')
        if not states or [chase,trans]!=states[-1][1:] or started:
            states.append([now,chase,trans])
        if trans['playing'] and not started:
            started=now
            with lock:
                saved.extend(blocks)
                retain=True
        if run=='reference' and started and not ended and now-started>17.6:
            c('transport.stop')
        if started and not trans['playing'] and not ended:
            ended=now
        if ended and now-ended>3.2: break
        time.sleep(.035)
finally:
    pathlib.Path(str(raw)+'.stop').touch()
    native.wait(timeout=8)
    if started and ended:
        with raw.open('rb') as src,(root/(base+'-native.bin')).open('wb') as dst:
            while h:=src.read(40):
                cb,ts,utc,pos,seq,n=struct.unpack('<QQQdII',h)
                pcm=src.read(4*n)
                if started-1.2<(utc-offset)/1e9<ended+3.4: dst.write(h+pcm)
    scratch.cleanup()
    stream.stop_stream()
    stream.close()
    ap.terminate()
    if run=='live': c('setup.mtc',online=False)
    if saved:
        with wave.open(str(root/(base+'.wav')),'wb') as w:
            w.setparams((channels,2,rate,0,'NONE',''))
            w.writeframes(b''.join(b[2] for b in saved))
    for port in ports:port.close_port()
    (root/(base+'-wire.json')).write_text(json.dumps(messages))
    out=dict(wall_qpc_offset_ns=offset,device=name,rate=rate,started=started,ended=ended,blocks=[[b[0],b[1],b[3]] for b in saved],states=states)
    (root/(base+'.json')).write_text(json.dumps(out))
    print(base,len(saved),started,ended,flush=True)

