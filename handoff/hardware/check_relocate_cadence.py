import json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'audio'))
from m1 import np
d=root/'runs/h4b-model12-02'
meta=json.loads((d/'driver/epoch-0.json').read_text())
n=meta['buffer'];rate=meta['qpc_frequency']
ty=np.dtype([('p','<u8'),('system','<u8'),('qpc','<u8'),('serial','<u8'),('flags','<i4'),('frames','<u4'),('pcm','<f4',(n,2))])
blocks=np.memmap(d/'driver/epoch-0.bin',dtype=ty,mode='r')
q=blocks['qpc'].astype(np.int64)*(10**9//rate)
polls=[json.loads(l) for l in (d/'transport.jsonl').read_text().splitlines()]
out=[]
for s in json.loads((d/'segments.json').read_text()):
    start=s['first'];end=s['last']
    states=[p for p in polls if start-1e9<=p[0]<=end+1e9]
    adds=[dict(earliest_s=(old[0]-start)/1e9,latest_s=(p[-1]-start)/1e9,count=p[1]['mtc_chase']['hard_relocates']) for old,p in zip(states,states[1:]) if p[1]['mtc_chase']['hard_relocates']>old[1]['mtc_chase']['hard_relocates']]
    def measure(lo,hi):
        a,b=np.searchsorted(q,[lo,hi])
        block=blocks[max(0,a-1):b+1]
        dt=np.diff(block['qpc'].astype(np.int64))*1000/rate
        return dict(intervals=len(dt),median_ms=float(np.median(dt)),max_ms=float(max(dt)),gaps_ge_200_ms=int(np.count_nonzero(dt>=200)),gaps_over_2_buffers=int(np.count_nonzero(dt>2*n/48)),sample_position_errors=int(np.count_nonzero(np.diff(block['p'])!=n)),serial_errors=int(np.count_nonzero(np.diff(block['serial'])!=1)))
    out.append(dict(qpc_start_ns=start,hard_relocation_brackets=adds,acquisition=measure(start,start+2500000000),whole_roll=measure(start,end)))
(root/'runs/h4b-before-storage-cadence.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))

