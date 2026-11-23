from pathlib import Path
import json, os, sys, time, wave, subprocess
d=Path(__file__).resolve().parent
sys.path[:0]=[str(d.parent),str(d.parent/'capture-deps')]
from desktop_sync import cmd
import rtmidi,numpy as np
p=json.loads((d/'control.json').read_text())['port']
audio=d/'duplex.bin';size=24+512*4
dtype=np.dtype([('ns','<u8'),('adc','<u8'),('serial','<u8'),('audio','<f4',(256,2))])
assert dtype.itemsize==size
def anchor():
    triples=[]
    for _ in range(25):
        a=time.perf_counter_ns();wall=time.time_ns();b=time.perf_counter_ns();triples.append((b-a,wall-(a+b)//2))
    return min(triples)
def take(name,spp):
    assert not cmd(p,'transport.status')['playing']
    mi=rtmidi.MidiIn();ports=mi.get_ports();mi.ignore_types(sysex=True,timing=False,active_sense=True);mi.open_port(next(i for i,n in enumerate(ports) if n.startswith('UM-ONE')))
    events=[]
    def incoming(ev,_):
        stamp=time.perf_counter()
        if ev[0] and ev[0][0] in (242,248,250,251,252):events.append((stamp,list(ev[0])))
    mi.set_callback(incoming)
    start=audio.stat().st_size//size;begin=anchor()
    try:
        time.sleep(.7)
        sub=subprocess.run([sys.executable,'exact_chorus.py',str(spp)],cwd=d,text=True,capture_output=True,timeout=15)
        assert sub.returncode==0,sub.stdout+sub.stderr
        time.sleep(1.5)
    finally:mi.close_port()
    end=anchor();n=audio.stat().st_size//size-start;assert n>600,(name,n)
    a=np.fromfile(audio,dtype=dtype,count=n,offset=start*size);assert (np.diff(a['serial'])==1).all() and (np.diff(a['ns'].astype('int64'))>0).all()
    assert abs(begin[1]-end[1])<800_000,(begin,end)
    delta=(begin[1]+end[1])//2
    b=(a['ns'].astype('int64')-delta)/1e9
    with wave.open(str(d/(name+'.wav')),'wb') as f:
        f.setparams((2,2,44100,0,'NONE',''));f.writeframes((np.clip(a['audio'],-1,.99996)*32768).astype('<i2').tobytes())
    ts=[[float(t),256,-int(adc)/1e9,''] for t,adc in zip(b,a['adc'])]
    (d/(name+'.json')).write_text(json.dumps(dict(spp=spp,midi=events,blocks=ts,serial_range=[int(a['serial'][0]),int(a['serial'][-1])],anchors_ns=[begin,end],transport=cmd(p,'transport.status'),source=sub.stdout)))
    print(name,spp,n,len(events),'peak',float(np.abs(a['audio']).max()),'ADC ms',float(np.median(a['adc']))/1e6,flush=True)
if __name__=='__main__':
    for n,k in [('exact-a',64),('late-a',65),('exact-b',64),('exact-c',64),('late-b',65),('exact-d',64)]:take(n,k)

