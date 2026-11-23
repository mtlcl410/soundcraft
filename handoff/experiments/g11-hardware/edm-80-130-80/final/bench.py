from pathlib import Path
import os,sys,json,time,wave,subprocess,socket,contextlib
d=Path(__file__).resolve().parent; hw=d.parent.parent
sys.path[:0]=[str(hw),str(hw/'capture-deps')]
from desktop_sync import cmd,rpc
import numpy as np,rtmidi,pyaudiowpatch as pa
def save(name,x): (d/(name+'.json')).write_text(json.dumps(x,indent=2))
def check(v,msg):
    if not v:raise AssertionError(msg)
def port(dev,label):
    i,=[i for i,n in enumerate(dev.get_ports()) if n.rsplit(' ',1)[0]==label]
    dev.open_port(i)
@contextlib.contextmanager
def app(song,label):
    exe=hw.parent/'g11-follow-r3-target/debug/soundcraft.exe'
    env=dict(os.environ,SOUNDCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(d/('prefs-'+label)),VST3_PATH='E:/S-MU2000-windows-x64/plugins',CLAP_PATH='E:/S-MU2000-windows-x64/plugins',S_MU2000_ROMS='E:/S-MU2000-windows-x64/roms')
    (d/('prefs-'+label)).mkdir(exist_ok=True)
    with socket.socket() as s:s.bind(('127.0.0.1',0));p=s.getsockname()[1]
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    with (d/(label+'.log')).open('w') as log:
        proc=subprocess.Popen([exe,'--control',str(p),str(song)],cwd=d,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,startupinfo=si)
    try:
        for _ in range(160):
            if proc.poll() is not None:raise RuntimeError('startup failed')
            try:cmd(p,'transport.status');break
            except OSError:time.sleep(.25)
        out=next(o['name'] for api in cmd(p,'ui.audio_device',list=True)['systems'] for o in api['outputs'] if 'S/PDIF' in o['name'])
        cmd(p,'ui.audio_device',output=out,sample_rate=48000,buffer_size=480)
        cmd(p,'setup.midi_clock_follow',enabled=False)
        yield lambda k,**v:rpc(p,'engine.execute',dict(command=k,params=v))
    finally:
        try:rpc(p,'app.quit',{});proc.wait(timeout=9)
        except Exception:proc.terminate();proc.wait(timeout=8)
@contextlib.contextmanager
def tap():
    dev=rtmidi.MidiIn();dev.ignore_types(sysex=False,timing=False,active_sense=True);port(dev,'UM-ONE');msgs=[]
    dev.set_callback(lambda e,_:msgs.append((time.perf_counter(),e[0])))
    try:yield msgs
    finally:dev.close_port()
@contextlib.contextmanager
def output():
    o=rtmidi.MidiOut();port(o,'Model 12 MIDI')
    try:yield o.send_message
    finally:o.close_port()
@contextlib.contextmanager
def capture(name):
    a=pa.PyAudio();z=next(z for z in a.get_loopback_device_info_generator() if 'S/PDIF' in z['name'])
    blocks=[];ch=z['maxInputChannels']
    assert int(z['defaultSampleRate'])==48000
    def cb(data,n,meta,flags):
        blocks.append((time.perf_counter(),data));return None,pa.paContinue
    s=a.open(format=pa.paInt16,channels=ch,rate=48000,input=True,input_device_index=z['index'],frames_per_buffer=480,stream_callback=cb)
    try:yield
    finally:
        s.stop_stream();s.close();a.terminate()
        with wave.open(str(d/(name+'.wav')),'wb') as w:w.setparams((ch,2,48000,0,'NONE',''));w.writeframes(b''.join(b for _,b in blocks))
        save(name+'-times',[(t,len(b)//(2*ch)) for t,b in blocks])
def qfs(send,frame,n):
    base=time.perf_counter()
    for i in range(n):
        f=frame+2*(i//8); sec,ff=divmod(f,30); minute,second=divmod(sec,60);hr,mi=divmod(minute,60)
        parts=[ff&15,ff>>4,second&15,second>>4,mi&15,mi>>4,hr&15,6|(hr>>4)]
        time.sleep(max(0,base+i/120-time.perf_counter()));send([241,16*(i%8)+parts[i%8]])
def full(sec):return [240,127,127,1,1,96,0,sec,0,247]
def audio(name):
    with wave.open(str(d/(name+'.wav'))) as w:return np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,w.getnchannels()).astype(float)
