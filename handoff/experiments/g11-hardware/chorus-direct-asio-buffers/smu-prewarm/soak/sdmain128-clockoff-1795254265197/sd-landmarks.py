from pathlib import Path
import sys, json, wave
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from timing import load_wave
case=Path(__file__).resolve().parent
src=next(case.glob('sd-*/manifest.json')).parent
rate=44100
record=json.loads((case/'record.json').read_bytes())
buf=record['buf']
anchor=sum(record['anchors'])//2
start=next(t+anchor for t,m in record['events'] if m==[248])
def captures(name):
 a=load_wave(case/(name+'.bin'))
 first=int(np.searchsorted(a['ns'],start))
 return a[first:first+int(rate*540/buf)]
def fetch(a,off,n):
 j,k=divmod(int(off),buf)
 with_blocks=a[j:j+(k+n+buf-1)//buf]['samples'][:,:buf,:]
 return with_blocks.reshape(-1,2)[k:k+n].copy()
usb=captures('in');out=captures('out')
def wav(ch):
 with wave.open(str(next(src.glob('*TR%02d.wav'%ch))),'rb') as f:
  a=np.frombuffer(f.readframes(f.getnframes()),np.uint8).reshape(-1,3)
  x=(a[:,2].astype(np.int8).astype(np.int32)<<16)+(a[:,1].astype(np.int32)<<8)+a[:,0]
  print('track',ch,'peak',np.max(np.abs(x)),flush=True)
  return x.astype(np.float32)/8388608
def corr_scores(s,r):
 s=s.astype('d');r=r.astype('d');r-=r.mean()
 size=1<<(len(s)+len(r)-1).bit_length()
 cc=np.fft.irfft(np.fft.rfft(s,size)*np.fft.rfft(r[::-1],size),size)[len(r)-1:len(s)]
 sums=np.r_[0.,s.cumsum()];ss=np.r_[0.,(s*s).cumsum()]
 e=(ss[len(r):]-ss[:-len(r)])-(sums[len(r):]-sums[:-len(r)])**2/len(r)
 return cc/np.sqrt(np.maximum(e,1e-19)*np.dot(r,r))
def best(s,r,center,span):
 lo=int(center)-span; pool=s[lo:int(center)+span+len(r)]
 scores=corr_scores(pool,r)
 i=int(scores.argmax());return lo+i,float(scores[i])
def coarse(s,channel):
 off=rate*2
 n=16384;dec=8
 ref=fetch(usb,off,n)[:,channel]
 limit=min(len(s),len(s)-539*rate+off+n+2*rate)
 ss=s[:limit//dec*dec].reshape(-1,dec).mean(axis=1)
 scores=corr_scores(ss,ref.reshape(-1,dec).mean(axis=1))
 choices=[]
 for _ in range(18):
  k=int(scores.argmax()); ix,score=best(s,ref,k*dec,24) if k>3 else (0,0)
  choices.append((score,ix-off));scores[max(0,k-512):k+513]=-1
 return max(choices)[1]
res={}
audio=json.loads((case.parent/('audio-'+case.name+'.json')).read_bytes())
trans=[c['time_s'] for i,c in enumerate(audio['chunks']) if i and c['lag']!=audio['chunks'][i-1]['lag']]
spots=sorted(set([.2,13.498,6.995,157.318,420.99785,421.04138,539.0]+[t+dt for t in trans for dt in (-1.1,-.1,.1,1.1)]))
for c in (0,1):
 digital=wav(11+c);analog=wav(3+c)
 off=coarse(digital,c);print('base',c,off,flush=True)
 landmarks=[]
 for sec in spots:
  pair=[]
  for dt in (-.04,.01):
   pos=round((sec+dt)*rate);n=1024
   ret=fetch(usb,pos,n)[:,c]
   sd,score=best(digital,ret,pos+off,192)
   an,ac=best(analog,digital[sd:sd+n],sd+38,80)
   pair.append(dict(sd_minus_usb=sd-pos,corr=score,analog_minus_sd=an-sd,analog_corr=ac))
  landmarks.append(dict(time=sec,checks=pair))
 res[c]=dict(base=off,landmarks=landmarks)
 del digital,analog
(case/'sd-landmarks.json').write_text(json.dumps(res,indent=2))
for ch,data in res.items():
 for spot in data['landmarks']:
  if abs(spot['time']-13.498)<.0001:print('target',ch,spot)

