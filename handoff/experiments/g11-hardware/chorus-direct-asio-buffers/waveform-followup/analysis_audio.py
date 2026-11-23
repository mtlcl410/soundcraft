from pathlib import Path
import sys,json,wave
d=Path(__file__).resolve().parent;src=d.parent
sys.path.insert(0,str(src))
from quality import np,stereo
rate=44100
def read(p):return json.loads(p.read_bytes())
def save(p,v):
 with wave.open(str(p),'wb') as w:
    w.setparams((2,2,rate,0,'NONE',''));w.writeframes(np.rint(v).clip(-32768,32767).astype('<i2').tobytes())
def pair(key):
 p=src/key;r=read(src/'metrics.json')[key]
 x=stereo(p.with_name(p.name+'-out.wav'));y=stereo(p.with_name(p.name+'-in.wav'));lag=r['lag_frames'];x=x[max(0,-lag):];y=y[max(0,lag):];n=min(len(x),len(y));x=x[:n];y=y[:n]
 # Derive stereo transfer from clean recordings only; a corrupted passage must not set the gain.
 clean=[v['transfer'] for v in read(src/'metrics.json').values() if v['peak_residual_step']<4];gain=np.median(clean,axis=0)
 return x@gain,y,r
if __name__=='__main__':
 import secrets
 examples=[('128','repeat-128/exact-a'),('64','repeat-64/late-b')]
 orders={};levels={}
 for label,key in examples:
    x,y,r=pair(key);start=max(0,int(np.flatnonzero(abs(x).max(1)>8)[0]) - rate//8);length=round(2.65*rate)
    a=x[start:start+length].copy();b=y[start:start+length].copy();gain=min(6,6800/max(abs(a).max(),abs(b).max()))
    for z in (a,b):
        z*=gain;z[:220]*=np.linspace(0,1,220)[:,None];z[-220:]*=np.linspace(1,0,220)[:,None]
    flip=secrets.randbelow(2);order=[a,b] if not flip else [b,a];orders[label]=['out','main'] if not flip else ['main','out']
    save(d/f'listen-{label}-AB.wav',np.vstack([np.zeros((4410,2)),order[0],np.zeros((round(.85*rate),2)),order[1],np.zeros((4410,2))]))
    levels[label]=gain
 (d/'listening-key.json').write_text(json.dumps({'order':orders,'linear_gain':levels,'excerpt_seconds':2.65,'pause_seconds':.85},indent=2))

