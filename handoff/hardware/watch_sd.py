"""Read only complete, already written ASIO callbacks at the end of the current file."""
import json,sys,time
from pathlib import Path
hw=Path(__file__).resolve().parent
sys.path.insert(0,str(hw/'audio'))
from m1 import np
from m1_app import cmd

def sample(epoch):
    meta=json.loads(epoch.read_text());n=meta['buffer'];rate=int(meta['sample_rate'])
    dtype=np.dtype([('hdr','<u8',(4,)),('flags','<i4'),('n','<u4'),('pcm','<f4',(n,2))])
    with epoch.with_suffix('.bin').open('rb') as f:
        count=f.seek(0,2)//dtype.itemsize
        length=min(count,(rate*5)//n)
        f.seek((count-length)*dtype.itemsize)
        blocks=np.frombuffer(f.read(length*dtype.itemsize),dtype=dtype)
    if length==0:return {}
    v=blocks['pcm'].reshape(-1,2)
    out={}
    for i,name in enumerate(('output1','input9')):
        edges=np.flatnonzero(abs(v[:,i])>.0005)
        idx=edges[np.r_[True,np.diff(edges)>3000]] if len(edges) else edges
        out[name]=dict(onsets=len(idx),peak=round(float(abs(v[:,i]).max()),6))
    return out
if __name__=='__main__':
    f=Path(sys.argv[1]);port=json.loads((f/'control.json').read_text())['port']
    with (f/'live-observations.jsonl').open('a',encoding='utf8',buffering=1) as log:
        while not (f/'stopped.json').exists():
            if (f/'environment-result.json').exists():raise RuntimeError('Measurement ended before stop')
            state=cmd(port,'transport.status')
            row=dict(qpc_ns=time.perf_counter_ns(),status=state,pcm=sample(f/'driver/epoch-0.json'))
            print(json.dumps(row),file=log);print(row,flush=True)
            for _ in range(45):
                if (f/'stopped.json').exists():break
                time.sleep(1)
        print('Computer transport stopped',flush=True)

