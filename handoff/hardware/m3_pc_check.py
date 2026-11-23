"""Inspect the captured PC copy once the shared ASIO stream is closed, before the SD readout."""
import json, sys, wave
from pathlib import Path
from sd_crosscheck import hw, np
def check(f):
    driver=f/'driver'
    m=json.loads((driver/'epoch-0.json').read_text())
    n=m['buffer'];sr=int(m['sample_rate'])
    dtype=np.dtype([('pos','<u8'),('sys','<u8'),('qpc','<u8'),('seq','<u8'),('flags','<i4'),('n','<u4'),('pcm','<f4',(n,2))])
    path=driver/'epoch-0.bin'
    if path.stat().st_size%dtype.itemsize:raise ValueError('Partial callback')
    b=np.memmap(path, mode='r', dtype=dtype)
    indices=[[],[]];prev=[-100000,-100000]
    for base in range(0,len(b),600):
        pcm=b[base:base+600]['pcm'].reshape(-1,2)
        for c in (0,1):
            v=np.flatnonzero(abs(pcm[:,c])>.0005)+base*n
            if len(v):
                indices[c].extend(map(int,v[np.diff(np.r_[prev[c],v])>12000]));prev[c]=int(v[-1])
    with wave.open(str(hw/'audio/manual-stimulus/sd-840s.wav')) as w:
        bank=np.empty((840,511),'f4')
        for k in range(840):
            w.setpos(k*sr+12000);bank[k]=np.sign(np.frombuffer(w.readframes(511),dtype='<i2'))
    ids=[{},{}];rejected=[[],[]]
    for c,hits in enumerate(indices):
        for j,i in enumerate(hits):
            row,off=divmod(i,n)
            sig=b[row:row+4]['pcm'].reshape(-1,2)[off:off+511,c]
            if len(sig)<511:continue
            denom=max(1e-12,float(np.linalg.norm(sig)*np.sqrt(511)))
            # Try the expected code first; if it differs, check the complete known sequence.
            k=min(j,len(bank)-1);score=abs(float(np.dot(bank[k],sig)))/denom
            if score<.85:
                vals=np.sum(bank*sig,axis=1)
                k=int(np.argmax(abs(vals)));score=abs(float(vals[k]))/denom
            if score<.85 or k in ids[c]:rejected[c].append([i,k,score]);continue
            ids[c][k]=i
    common=sorted(ids[0].keys() & ids[1].keys())
    if not common:raise ValueError('No matching output and return')
    def pos(i):row,off=divmod(i,n);return int(b['pos'][row])+off
    def qpc(i):row,off=divmod(i,n);return float(b['qpc'][row])/m['qpc_frequency']+off/sr
    lo=ids[0][common[0]]//n;hi=ids[1][common[-1]]//n+1
    measured=b[lo:hi]
    def gaps(x):
        return dict(position=int(np.count_nonzero(np.diff(x['pos'])!=n)),sequence=int(np.count_nonzero(np.diff(x['seq'])!=1)),invalid_flags=int(np.count_nonzero((x['flags']&2)==0)),buffer_mismatch=int(np.count_nonzero(x['n']!=n)))
    offsets=[pos(ids[1][k])-pos(ids[0][k]) for k in common]
    result=dict(output_codes=len(ids[0]),input9_codes=len(ids[1]),matched=len(common),first_code=common[0],last_code=common[-1],
        matched_span_s=(pos(ids[1][common[-1]])-pos(ids[1][common[0]]))/sr,
        host_qpc_span_s=qpc(ids[1][common[-1]])-qpc(ids[1][common[0]]),
        missing_internal=[i for i in range(common[0],common[-1]+1) if i not in common],
        unexpected=rejected,whole_stream_gaps=gaps(b),measurement_gaps=gaps(measured),min_loop_samples=min(offsets),max_loop_samples=max(offsets))
    (f/'pc-markers.json').write_text(json.dumps(result,indent=2))
    print(result)
if __name__=='__main__':check(Path(sys.argv[1]))

