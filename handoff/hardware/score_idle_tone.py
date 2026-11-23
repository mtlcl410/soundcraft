"""Find the recorded A4 independently on the two native channels."""
import json, sys, wave
from pathlib import Path
from storage_i24_control import np
def score(run):
    with wave.open(str(run/'a4.wav'),'rb') as wav:
        wav.setpos(5*48000)
        ref=np.frombuffer(wav.readframes(12000),'<i2').astype(float)/32768
    result={}
    for name,(a,b) in json.loads((run/'windows.json').read_text()).items():
        if not name.startswith('play-'): continue
        result[name]={}
        for ep in (run/'driver').glob('epoch-*.json'):
            m=json.loads(ep.read_text())
            n,hz=m['buffer'],m['qpc_frequency']
            dt=np.dtype([('pos','<u8'),('sys','<u8'),('q','<u8'),('s','<u8'),('flags','<i4'),('n','<u4'),('pcm','<f4',(n,2))])
            count=ep.with_suffix('.bin').stat().st_size//dt.itemsize
            if not count: continue
            raw=np.memmap(ep.with_suffix('.bin'),mode='r',dtype=dt,shape=(count,))
            lo,hi=np.searchsorted(raw['q'],np.array([a,b],dtype=float)*hz/1e9)
            if hi-lo<1400:continue
            data=raw[lo:hi]['pcm'].reshape(-1,2)
            for i,ch in enumerate(['out1','in9']):
                x=data[:,i].astype(float)
                size=1<<int(np.ceil(np.log2(len(x)+len(ref))))
                corr=np.fft.irfft(np.fft.rfft(x,size)*np.conj(np.fft.rfft(ref,size)),size)[:len(x)-len(ref)+1]
                k=int(np.argmax(np.abs(corr))); v=x[k:k+len(ref)]
                norm=float(np.linalg.norm(v)*np.linalg.norm(ref))
                result[name][ch]=dict(peak=float(np.max(np.abs(v))),correlation=float(corr[k]/norm) if norm else None,window_s=k/48000)
    (run/'a4.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=='__main__':score(Path(sys.argv[1]))
