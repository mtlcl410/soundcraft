"""Read-only cadence analysis of the raw ASIO evidence, by physical MTC roll."""
import csv,json,sys
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'audio'))
from m1 import np
d=root/'runs/h3b-model12-01'
meta=json.loads((d/'driver/epoch-0.json').read_text())
n,hz=meta['buffer'],meta['qpc_frequency']
ty=np.dtype([('position','<u8'),('system','<u8'),('qpc','<u8'),('serial','<u8'),('flags','<i4'),('frames','<u4'),('pcm','<f4',(n,2))])
a=np.memmap(d/'driver/epoch-0.bin',dtype=ty,mode='r')
ns=a['qpc'].astype(np.int64)*(10**9//hz)
assert 10**9%hz==0 and np.all(np.diff(ns)>0)
def select(t0,t1):
    s=a[(ns>=t0)&(ns<=t1)]
    dt=np.diff(s['qpc'].astype(np.int64))*1000/hz
    edges=[0,2,4,7,10,50,200,240,260,float('inf')]
    hist=np.histogram(dt,bins=edges)[0]
    return dict(callbacks=len(s),intervals=len(dt),median_ms=float(np.median(dt)),mean_ms=float(np.mean(dt)),min_ms=float(min(dt)),max_ms=float(max(dt)),p99_ms=float(np.percentile(dt,99,method='higher')),
        bins=hist.tolist(),pos_deltas=dict(Counter(map(str,np.diff(s['position'].astype(np.int64))))),serial_skips=int(np.count_nonzero(np.diff(s['serial'])!=1)),frames=sorted(set(map(int,s['frames']))),position_valid=int(np.count_nonzero((s['flags']&2)!=0)),flags=dict(Counter(map(str,s['flags']))))
result={}
for name in ('baseline','post-1','post-2','post-3'):
    p=d/name
    st=json.loads((p/'offset.json').read_text());t=round(st['anchor_qpc_s']*1e9)
    with (p/'rx.csv').open() as f:
        q=[int(r['qpc_ns']) for r in csv.DictReader(f) if r['hex'].startswith('f1')]
    res=dict(roll_span_ms=(q[-1]-q[0])/1e6,qframes=len(q),decoded_reference_scatter_ms=st['wire_scatter_ms'],a4=st['channels'],roll=select(q[0],q[-1]),around_a4=select(t-10**9,t+10**9))
    result[name]=res
    print(name,res['roll'],res['around_a4']['bins'])
(root/'runs/asio-environment-histogram.json').write_text(json.dumps(result,indent=2))

