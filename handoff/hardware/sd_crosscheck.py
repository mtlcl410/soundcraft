"""Compare the same coded click at USB out, USB return, SD track and the host QPC clock."""
import argparse, ctypes, csv, hashlib, json, shutil, struct, wave
from pathlib import Path
import sys
hw=Path(__file__).resolve().parent
sys.path.insert(0,str(hw/'audio'))
from m1 import np,read_blocks

def wav_layout(path):
    with path.open('rb') as f:
        header=f.read(12)
        if header[:4]!=b'RIFF' or header[8:]!=b'WAVE':raise ValueError(path)
        fmt=None
        while tag:=f.read(8):
            chunk,size=struct.unpack('<4sI',tag);offset=f.tell()
            if chunk==b'fmt ':fmt=struct.unpack_from('<HHIIHH',f.read(min(40,size)))
            if chunk==b'data' and fmt:
                code,ch,sr,_,align,bits=fmt
                if code not in (1,65534) or sr!=48000 or bits not in (16,24) or ch!=1:raise ValueError((path,fmt))
                if offset+size>path.stat().st_size:raise ValueError('Truncated SD WAV')
                return offset,size,bits,ch
            f.seek(offset+size+(size%2))
    raise ValueError('Missing WAV format or data')

def sd_samples(path):
    offset,size,bits,_=wav_layout(path)
    if bits==16:return np.memmap(path,offset=offset,dtype='<i2',mode='r',shape=(size//2,))
    return np.memmap(path,offset=offset,dtype='u1',mode='r',shape=(size//3,3))

def samples(a,lo,hi):
    d=a[lo:hi]
    if d.ndim==1:return np.asarray(d,dtype='f4')
    raw=d.astype(np.int32)
    w=raw[:,0]+(raw[:,1]<<8)+(raw[:,2]<<16)
    return ((w^0x800000)-0x800000).astype('f4')/8388608.

def peaks(a,level):
    starts=[];last=-100000
    for lo in range(0,len(a),48000):
        chunk=samples(a,lo,lo+48000)
        v=np.flatnonzero(abs(chunk)>level)+lo
        if len(v):
            starts.extend(int(x) for x in v[np.diff(np.r_[last,v])>12000])
            last=int(v[-1])
    return starts

def marks(a, bank, level):
    hits={}; ambiguous=[]
    for onset in peaks(a,level):
        x=samples(a,onset,onset+511)
        if len(x)!=511:continue
        # All 840 codes have equal energy. Elementwise reduction avoids BLAS thread fanout.
        scores=np.sum(bank*x,axis=1)/max(1e-15,np.linalg.norm(x)*np.sqrt(511))
        i=int(np.argmax(abs(scores)))
        if abs(scores[i])<.85:ambiguous.append([onset,round(float(scores[i]),4)]);continue
        if i in hits:raise ValueError(f'Duplicate code {i}')
        hits[i]=onset
    return hits,ambiguous

def copy(song,folder):
    if len(song.split('_'))!=2 or not all(x.isdigit() for x in song.split('_')):raise ValueError('Expected Model 12 song ID')
    choices=[Path(f'{c}:/MTR')/song for c in 'DEFGHIJKLMNOPQRSTUVWXYZ' if ctypes.windll.kernel32.GetDriveTypeW(f'{c}:\\')==2 and (Path(f'{c}:/MTR')/song).is_dir()]
    if len(choices)!=1:raise ValueError(f'Cannot identify unique removable source {choices}')
    dest=folder/'sd'/song;dest.mkdir(parents=True,exist_ok=True)
    files=[]
    for ch in (9,10):
        src,=choices[0].glob(f'*_TR{ch:02d}.wav');target=dest/src.name
        if not target.exists():shutil.copyfile(src,target)
        def digest(p):
            with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
        if digest(src)!=digest(target):raise ValueError(target)
        files.append(dict(name=target.name,bytes=target.stat().st_size,sha256=digest(target)))
    (dest/'manifest.json').write_text(json.dumps(files,indent=2)); print(files)

def analyse(f,path):
    with wave.open(str(hw/'audio/manual-stimulus/sd-840s.wav')) as w:
        bank=np.empty((840,511),dtype='f4')
        for k in range(840):
            w.setpos(k*48000+12000)
            bank[k]=np.sign(np.frombuffer(w.readframes(511),dtype='<i2'))
    meta,pcm,b=read_blocks(f/'driver')
    sd=sd_samples(path)
    out,_=marks(pcm[:,0],bank,.0005);ret,_=marks(pcm[:,1],bank,.0005);disk,unmatched=marks(sd,bank,.0005)
    common=sorted(set(out)&set(ret)&set(disk))
    if len(common)<2:raise ValueError('No common coded reference')
    first,last=common[0],common[-1];sr=48000;n=meta['buffer']
    def host(i):return int(b['qpc'][i//n])/meta['qpc_frequency']+(i%n)/sr
    with (f/'sd-drift-pairs.csv').open('w',newline='') as csvfile:
        rows=csv.writer(csvfile);rows.writerow(['code_index','asio_output','asio_input9','sd','host_s_input'])
        for i in common:rows.writerow([i,out[i],ret[i],disk[i],host(ret[i])])
    dsd=disk[last]-disk[first];dret=ret[last]-ret[first];dt=host(ret[last])-host(ret[first])
    result=dict(matched=len(common),first_code=first,last_code=last,span_s=dsd/sr,missing_inside=[i for i in range(first,last+1) if i not in common],unmatched_sd=unmatched,
        sd_minus_usb_samples=dsd-dret,sd_minus_usb_ppm=(dsd/dret-1)*1e6,host_qpc_span_s=dt,sd_minus_host_ppm=(dsd/sr/dt-1)*1e6,
        min_loop_samples=min(ret[i]-out[i] for i in common),max_loop_samples=max(ret[i]-out[i] for i in common))
    (f/'sd-drift.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':
    mode,folder,other=sys.argv[1:];f=Path(folder)
    if mode=='copy':copy(other,f)
    else:analyse(f,Path(other))

