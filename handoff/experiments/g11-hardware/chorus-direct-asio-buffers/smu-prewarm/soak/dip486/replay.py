"""Same captured PCM through a separate full-duplex ASIO client, at native buffer size."""
import os,sys,time,json
from pathlib import Path
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent))
from inspect_dips import root,read,np,rate,segment,load_wave
os.environ['SD_ENABLE_ASIO']='1'
sys.path.insert(0,str(Path(os.environ['TEMP'])/'soundcraft-chorus-pa441'))
import sounddevice as sd
b=int(sys.argv[1]);target=next(v for v in read(root/'dips-long64.json') if v['quiet_samples']==64)['out_frame']
source=(segment(load_wave(root/'long64'/'out.bin'),target-16384,32768,64)/32768).astype('float32')
source[:128]*=np.linspace(0,1,128)[:,None];source[-128:]*=np.linspace(1,0,128)[:,None]
# Four uninterrupted and four delayed transfers in a balanced order. All receive identical PCM.
modes=[False,True,True,False,True,False,False,True];stride=65536
sig=np.zeros(((len(modes)+1)*stride,2),'float32');targets=[]
for i,hold in enumerate(modes,1):
    base=i*stride-16384;sig[base:base+len(source)]=source;targets.append(i*stride)
rec=np.zeros_like(sig);delay_at={v for v,h in zip(targets,modes) if h}
nrows=len(sig)//b+4096;log=np.zeros((nrows,6),dtype='int64')
pos=0;nr=0;err=None;previous=0
def callback(ins,out,n,t,flags):
    global nr,pos,previous,err
    entry=time.perf_counter_ns()
    if n!=b or nr>=len(log):
        err=(n,nr);out.fill(0);raise sd.CallbackAbort
    if pos in delay_at:
        # Recreate the observed ~6.50 ms interval between deliveries before publishing this block.
        wait=(previous+6_500_000-entry)/1e9
        if wait>0:time.sleep(wait)
    ready=time.perf_counter_ns()
    out.fill(0)
    count=min(n,len(sig)-pos)
    if count>0:out[:count]=sig[pos:pos+count];rec[pos:pos+count]=ins[:count]
    log[nr]=[pos,n,entry,ready,time.perf_counter_ns(),flags._flags]
    previous=entry;pos+=n;nr+=1
dev=next(i for i,n in enumerate(sd.query_devices()) if n['name']=='Model Mixer ASIO')
with sd.Stream(device=(dev,dev),samplerate=rate,channels=2,dtype='float32',blocksize=0,extra_settings=(sd.AsioSettings(channel_selectors=[10,11]),sd.AsioSettings(channel_selectors=[8,9])),callback=callback) as stream:
    stop=time.monotonic()+22
    while pos<len(sig) and stream.active and time.monotonic()<stop:time.sleep(.01)
assert pos>=len(sig) and err is None,(pos,err)
np.savez(here/f'replay-{b}.npz',source=source,recording=rec,calls=log[:nr],targets=targets,held=modes)
print('ASIO',b,'observed sizes',np.unique(log[:nr,1]),'trials',len(targets),'status flag counts',np.unique(log[:nr,5],return_counts=True))

