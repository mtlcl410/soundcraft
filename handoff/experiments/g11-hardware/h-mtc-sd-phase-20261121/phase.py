from pathlib import Path
from itertools import combinations
import sys,json,statistics
root=Path(__file__).resolve().parent
source=root.parent/'h-mtc-sd-20261121-211205'
sys.path.insert(0,str(source.parent/'capture-deps'))
import numpy as np
def read(name):
 return [json.loads(line) for line in (source/name).read_text().splitlines()]
def decode(p):
 return ((p[6]+((p[7]&1)<<4))*3600+(p[4]+16*p[5])*60+p[2]+16*p[3])*30+p[0]+16*p[1]
def percentile(x,p):
 return round(float(np.percentile(x,p)),3)
out={}
for tag in ['take1','take2r','take3r']:
 wire=read(tag+'-wire.jsonl')
 ts=np.array([(t,d[1]) for t,p,d in wire if p.startswith('UM-ONE') and d[0]==241],dtype=np.int64)
 t=ts[:,0]; b=ts[:,1]
 groups=[]
 for i in range(7,len(t)):
  if list(b[i-7:i+1]>>4)==list(range(8)):
   frame=decode(b[i-7:i+1]&15)
   groups.append((t[i-7],frame,t[i]))
 g=np.array(groups)
 # Use groups within 1 second on either side of the 5 s A4, well before the cable pull.
 group=g[(g[:,1]>=120)&(g[:,1]<=180)]
 wire_zero=int(np.median(group[:,0]-group[:,1]*(1e9/30)))
 wires=np.diff(t)/1e6
 states=read(tag+'-transport.jsonl')
 live=[r for r in states if r.get('mtc',{}).get('state')=='Locked' and r.get('transport',{}).get('playing') and 4e9 < r['monotonic_ns']-wire_zero < 6e9]
 # RPC contains two calls. The transport read may occur anywhere in this interval, with device-block granularity.
 residual=lambda r,k: (r[k]-wire_zero)/1e6-r['transport']['position']/48
 out[tag]=dict(first_frame=int(g[0,1]),first_group_0_to_7_ms=(g[0,2]-g[0,0])/1e6,first_0_to_second_7_ms=(g[1,2]-g[0,0])/1e6,
 qf_interval_ms=[percentile(wires,p) for p in (5,50,95)], qf0_scatter_at_A4_ms=[percentile((group[:,0]-group[:,1]*(1e9/30)-wire_zero)/1e6,p) for p in (5,95)],
 reader_input_jitter_p95_ms=percentile([r['mtc']['input_jitter_p95_us']/1000 for r in live],50),
 reader_arrival_p95_ms=percentile([r['mtc']['arrival_delay_p95_us']/1000 for r in live],50),
 rpc_cursor_lag_bounds_median_ms=[percentile([residual(r,k) for r in live],50) for k in ['monotonic_ns','reply_ns']],polls=len(live),
 relocates=[r['mtc']['hard_relocates'] for r in [live[0],live[-1]]])
onset=json.loads((source/'anchor-crosscheck.json').read_text())
out['pairs']={}
for a,b in combinations(onset,2):
 delta=onset[b]['template_ms']-onset[a]['template_ms']
 out['pairs'][a+'-'+b]=dict(delta_ms=round(delta,3),frame_residual_ms=round(delta-round(delta*30/1000)*1000/30,3),quarter_residual_ms=round(delta-round(delta*120/1000)*1000/120,3))
(root/'three-run-phase.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
