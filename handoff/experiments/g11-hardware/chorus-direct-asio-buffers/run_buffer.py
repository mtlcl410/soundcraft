from pathlib import Path
import os,sys,time,json,shutil,subprocess,wave,hashlib
d=Path(__file__).resolve().parent;old=d.parent/'chorus-direct-asio'
sys.path[:0]=[str(d.parent),str(d.parent/'capture-deps')]
from desktop_sync import cmd
import numpy as np,rtmidi
buf=int(sys.argv[1]); assert buf in (64,128,256)
case=d/sys.argv[2];case.mkdir()
os.environ.update(SC_ASIO_WITNESS=str(case/'in.bin'),SC_OUTPUT_WITNESS=str(case/'out.bin'),PYTHONUTF8='1')
for name in ('exact_chorus.py','launch.py'):
 s=(old/name).read_text().replace('str(here.parent)', 'str(here.parent.parent)').replace('here.parent/"capture-deps"','here.parent.parent/"capture-deps"')
 if name=='launch.py':
    s=s.replace("old=here/'session'","old=here.parent.parent/'chorus-direct-asio'/'session'").replace("exe=here/'soundcraft.exe'","exe=here.parent/'soundcraft.exe'").replace('buffer_size=256','buffer_size='+str(buf))
 (case/name).write_text(s)
typ=np.dtype([('ns','<u8'),('adc','<u8'),('serial','<u8'),('size','<u8'),('samples','<f4',(256,2))])
def mark():
 tri=[]
 for _ in range(24):
    a=time.perf_counter_ns();v=time.time_ns();b=time.perf_counter_ns();tri.append((b-a,v-(a+b)//2))
 return min(tri)
def subset(file,begin,end):
 n=file.stat().st_size//typ.itemsize
 a=np.memmap(file,dtype=typ,mode='r',shape=(n,))
 return np.array(a[(a['ns']>=begin)&(a['ns']<=end)])
def take(name,spp,port):
 assert not cmd(port,'transport.status')['playing']
 mi=rtmidi.MidiIn();mi.ignore_types(sysex=True,timing=False,active_sense=True);mi.open_port(next(i for i,p in enumerate(mi.get_ports()) if p.startswith('UM-ONE')))
 events=[]
 def cb(ev,_):
    now=time.perf_counter()
    if ev[0] and ev[0][0] in (242,248,250,251,252):events.append((now,list(ev[0])))
 mi.set_callback(cb);begin=time.time_ns();x=mark()
 try:
    time.sleep(.5)
    s=subprocess.run([sys.executable,'exact_chorus.py',str(spp)],cwd=case,text=True,capture_output=True,timeout=13);assert not s.returncode,s.stdout+s.stderr
    time.sleep(1.5)
 finally:mi.close_port()
 y=mark();end=time.time_ns();tsdelta=(x[1]+y[1])//2;assert abs(x[1]-y[1])<800000
 time.sleep(.13)
 meta=dict(spp=spp,events=events,anchors=[x,y],final=cmd(port,'transport.status'))
 for k in ('in','out'):
    a=subset(case/(k+'.bin'),begin,end); assert len(a)>600 and (a['size']==buf).all(),(k,len(a),np.unique(a['size']))
    meta[k]=dict(serial_gaps=int(np.count_nonzero(np.diff(a['serial'])!=1)),ns=(a['ns'].astype('int64')-tsdelta).tolist(),adc=np.unique(a['adc']).tolist(),size=buf,count=len(a))
    z=a['samples'][:,:buf,:].reshape(-1,2)
    with wave.open(str(case/(name+'-'+k+'.wav')),'wb') as w:
        w.setparams((2,2,44100,0,'NONE',''));w.writeframes((np.clip(z,-1,.999969)*32768).astype('<i2').tobytes())
 (case/(name+'.json')).write_text(json.dumps(meta))
 print(name,meta['in']['count'],meta['out']['count'],len(events),flush=True)
try:
 p=subprocess.run([sys.executable,'launch.py'],cwd=case,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=75);(case/'launch.log').write_text(p.stdout);assert not p.returncode,p.stdout
 port=json.loads((case/'control.json').read_bytes())['port'];time.sleep(2)
 snap={}
 for k in ('in','out'):
    f=case/(k+'.bin');n=f.stat().st_size//typ.itemsize
    a=np.fromfile(f,dtype=typ,count=n);snap[k]=np.unique(a['size']).tolist();assert snap[k],k
 (case/'actual.json').write_text(json.dumps(dict(requested=buf,actual=snap,route=json.loads((case/'route.json').read_bytes())),indent=2));print(buf,snap,flush=True)
 if all(v==[buf] for v in snap.values()):
    for name,spp in [('exact-a',64),('late-a',65),('exact-b',64),('exact-c',64),('late-b',65),('exact-d',64)]:take(name,spp,port)
finally:
 if (case/'control.json').exists():
    port=json.loads((case/'control.json').read_bytes())['port']
    try:cmd(port,'app.quit')
    except OSError:pass
 time.sleep(1.2)

