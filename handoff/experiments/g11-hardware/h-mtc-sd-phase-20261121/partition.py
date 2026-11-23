from pathlib import Path
import sys,json,statistics
from analyse import np,pcm
d=Path(__file__).resolve().parent
old=d.parent/'h-mtc-sd-20261121-211205'
sr=48000
ref=pcm(next((old/'take1').glob('*/*_TR02.wav')))[240648:244248].copy()

def match(x,template):
 t=template-template.mean(); n=len(t)
 sq=np.r_[0.,np.cumsum(x*x)]; sums=np.r_[0.,np.cumsum(x)]
 energy=np.maximum(1e-18,sq[n:]-sq[:-n]-(sums[n:]-sums[:-n])**2/n)
 prod=np.correlate(x,t,mode='valid')
 corr=prod/np.sqrt(energy*np.dot(t,t))
 i=int(np.argmax(abs(corr)))
 return i,float(corr[i])

class Audio:
 def __init__(self,prefix):
  self.blocks=np.loadtxt(prefix.with_suffix('.csv'),delimiter=',',skiprows=1,dtype=np.int64,ndmin=2)
  self.file=np.memmap(prefix.with_suffix('.f32'),dtype='<f4',mode='r').reshape(-1,2)
 def at(self,t):
  i=np.searchsorted(self.blocks[:,3],t*1e7,side='right')-1
  assert 0<=i<len(self.blocks)
  offset,length,pos,stamp,flags=self.blocks[i]
  return round(int(offset)+(t-stamp/1e7)*sr)
 def time(self,i):
  j=int(np.searchsorted(self.blocks[:,0],i,side='right')-1)
  offset,length,pos,stamp,flags=self.blocks[j]
  assert 0<=i-offset<length and not flags&4
  return stamp/1e7+(i-offset)/sr
 def find(self,t,channel,template,radius=.22):
  center=self.at(t);a=max(0,center-round(sr*radius));z=min(len(self.file),center+round(sr*radius)+len(template))
  if z-a<len(template):return None
  rows=self.blocks[(self.blocks[:,0]<z)&(self.blocks[:,0]+self.blocks[:,1]>a)]
  if (rows[:,4]&5).any():return None
  i,score=match(np.array(self.file[a:z,channel],dtype='float64'),template)
  return self.time(a+i),score

def wire(p):
 data=np.loadtxt(p/'wire.csv',delimiter=',',skiprows=1,dtype=np.int64,ndmin=2)
 # MIDI short messages are packed little endian by WinMM.
 rows=data[(data[:,3]&255)==241]; times=rows[:,0]/rows[:,1]; data=(rows[:,3]>>8)&127
 runs=np.split(np.arange(len(rows)),np.where(np.diff(times)>0.7)[0]+1)
 result=[]
 for ix in runs:
  if len(ix)<240:continue
  groups=[]
  for j in range(7,len(ix)):
   i=int(ix[j]); p8=data[i-7:i+1]
   if list(p8>>4)!=list(range(8)):continue
   n=p8&15
   frame=int((n[6]+(n[7]&1)*16)*108000+(n[4]+n[5]*16)*1800+(n[2]+n[3]*16)*30+n[0]+n[1]*16)
   groups.append((frame,times[i-7],rows[i-7,2]))
  near=[(f,t,m) for f,t,m in groups if 120<=f<=180]
  assert len(near)>=20, (len(ix),len(near))
  zero=np.median([t-f/30 for f,t,_ in near]); spread=np.ptp([t-f/30 for f,t,_ in near])*1000
  result.append((float(zero),round(float(spread),3),len(ix),groups[0][0]))
 return result

def analyze(p,run_index,song):
 cap=Audio(p/'input'); loop=Audio(p/'loop')
 z,wire_scatter,count,frame=wire(p)[run_index]
 ch1=pcm(next(song.glob('*_TR01.wav')));ch2=pcm(next(song.glob('*_TR02.wav')))
 i,cc=match(ch2[round(4.7*sr):round(5.45*sr)],ref)
 anchor=4.7+i/sr
 has_sd=abs(cc)>.9
 report={'song':song.name,'din_pieces':count,'first_qf_label_frames':frame,'qf0_scatter_peak_to_peak_ms':wire_scatter,'sd_onset_ms':round((anchor-5)*1000,3) if has_sd else None,'sd_match':round(cc,4)}
 loop_matches=[loop.find(z+5,ch,ref) for ch in range(2)]
 loop_matches=[v for v in loop_matches if v]
 lt,lcc=max(loop_matches,key=lambda v:abs(v[1]),default=(0,0))
 direct=(lt-z-5)*1000
 report.update(render_tap_minus_wire_ms=round(direct,3) if abs(lcc)>.9 else None,render_match=round(lcc,4))
 anchors=[]
 start=round(frame/30) # first group normally two frames ahead
 for a,b in [(start+.6,start+4.4),(start+5.4,min(len(ch1)/sr-.2,start+10.5))]:
  if b-a<.061:continue
  # Highest-energy 60 ms microphone window within each cue's search range.
  lo=int(a*sr);n=int(.06*sr);energy=np.convolve(ch1[lo:int(b*sr):16]**2,np.ones(n//16),mode='valid')
  if not len(energy):continue
  k=lo+16*int(energy.argmax())
  if float(np.max(np.abs(ch1[k:k+n])))<.001:continue
  choices=[(v,ch) for ch in range(2) if (v:=cap.find(z+k/sr,ch,ch1[k:k+n]))]
  (at,coef),ch=max(choices,key=lambda v:abs(v[0][1]),default=((0,0),-1))
  anchors.append(dict(song_s=round(k/sr,4),usb_capture_channel=ch+1,correlation=round(coef,4),capture_origin_minus_wire_ms=round((at-k/sr-z)*1000,3) if abs(coef)>.85 else None))
 report['mic_markers']=anchors
 good=[a['capture_origin_minus_wire_ms'] for a in anchors if a['capture_origin_minus_wire_ms'] is not None]
 if len(good)==2 and abs(good[0]-good[1])<=2 and has_sd and abs(lcc)>.9:
  common=statistics.mean(good)
  report['sd_backing_as_seen_on_capture_clock_minus_render_tap_ms']=round((anchor-5)*1000+common-direct,3)
 return report
if __name__=='__main__':
 p=d/sys.argv[1]
 reports=[analyze(p,i,Path(song)) for i,song in enumerate(sys.argv[2:])]
 (p/'partition.json').write_text(json.dumps(reports,indent=2))
 print(json.dumps(reports,indent=2))
