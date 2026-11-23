from pathlib import Path
import json,struct,sys,wave
from storage_i24_control import np

def measure(run):
    with wave.open(str(run/'a4.wav'),'rb') as f:
        f.setpos(5*48000); ref=np.frombuffer(f.readframes(12000),'<i2').astype(float)/32768
    rows=[]
    for file in run.rglob('*.wav'):
        if file.name=='a4.wav':continue
        data=file.read_bytes();pos=12;fmt=payload=None
        while pos+8<=len(data):
            size=struct.unpack_from('<I',data,pos+4)[0]
            chunk=data[pos:pos+4]
            if chunk==b'fmt ':fmt=data[pos+8:pos+8+size]
            if chunk==b'data':payload=data[pos+8:pos+8+size]
            pos+=8+size+(size%2)
        kind,channels,hz,_,_,bits=struct.unpack_from('<HHIIHH',fmt)
        if kind==65534:kind=struct.unpack_from('<H',fmt,24)[0]
        assert channels==1 and hz==48000 and bits==32,(channels,hz,bits)
        x=np.frombuffer(payload,'<f4' if kind==3 else '<i4').astype(float)
        if kind==1:x/=2147483648.
        n=1<<int(np.ceil(np.log2(len(x)+len(ref))))
        corr=np.fft.irfft(np.fft.rfft(x,n)*np.fft.rfft(ref,n).conj(),n)[:len(x)-len(ref)+1]
        k=int(np.argmax(abs(corr)))
        v=x[k:k+len(ref)]
        den=np.linalg.norm(v)*np.linalg.norm(ref)
        rows.append(dict(file=str(file.relative_to(run)),frames=len(x),seconds=len(x)/hz,peak=float(np.max(abs(x))),tone_s=k/hz,correlation=float(corr[k]/den) if den else None))
    (run/'takes.json').write_text(json.dumps(rows,indent=2))
    print(rows)
if __name__=='__main__':measure(Path(sys.argv[1]))
