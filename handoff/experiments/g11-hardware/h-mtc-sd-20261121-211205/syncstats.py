from pathlib import Path
import sys,json,statistics
base=Path(__file__).resolve().parent
name=sys.argv[1]
def load(f):
 rows=[]
 for ln in f.read_text(encoding='utf8').splitlines():
  try: rows.append(json.loads(ln))
  except ValueError: pass
 return rows
wire=load(base/(name+'-wire.jsonl'))
states=load(base/(name+'-transport.jsonl'))
q=[t for t,p,b in wire if p.startswith('UM-ONE') and b[0]==241]
if not q:sys.exit('No incoming quarter frames')
q0=q[0]
gap=max(range(1,len(q)),key=lambda i:q[i]-q[i-1])
g0=q[gap-1]
g1=q[gap]
def state(r):return r.get('mtc',{}).get('state','unknown')
def playing(r):return r.get('transport',{}).get('playing')
live=[r for r in states if q0-500_000_000<=r['monotonic_ns']<=q[-1]+4_000_000_000]
if not live:sys.exit('No transport samples in range')
def sec(n):return round(n/1e9,4)
def ms(n):return round(n/1e6,2)
def first(pred):return next((r for r in live if pred(r)),None)
s0=first(lambda r:playing(r) and state(r)=='Locked')
end=first(lambda r:r['monotonic_ns']>=q[-1] and playing(r)==False)
info=dict(um_one_qf=len(q),wire_span_s=sec(q[-1]-q0),session_record_true=sum(playing(r) is not None and r['transport']['recording'] for r in live),rpc_errors=sum('error'in r for r in live),frame_rates=sorted({r['mtc']['incoming_rate'] for r in live if 'mtc'in r and r['mtc']['incoming_rate']}),first_lock_poll_ms_after_first_qf=ms(s0['monotonic_ns']-q0) if s0 else None,stop_poll_ms_after_last_qf=ms(end['monotonic_ns']-q[-1]) if end else None,largest_qf_gap_ms=ms(g1-g0),rate_mismatch_polls=sum(bool(r.get('mtc',{}).get('rate_mismatch')) for r in live),observation_period_ms=ms(statistics.median([b['monotonic_ns']-a['monotonic_ns'] for a,b in zip(live,live[1:])])))
if g1-g0>150_000_000:
 loss=first(lambda r:r['monotonic_ns']>=g0 and r['monotonic_ns']<g1 and playing(r)==False)
 back=first(lambda r:r['monotonic_ns']>=g1 and playing(r) and state(r)=='Locked')
 near=[r for r in live if g0-200_000_000<=r['monotonic_ns']<=g1+650_000_000]
 info['cable']=dict(last_qf_elapsed_s=sec(g0-q0),first_qf_back_elapsed_s=sec(g1-q0),stop_poll_ms_after_last_good=ms(loss['monotonic_ns']-g0) if loss else None,relock_poll_ms_after_return=ms(back['monotonic_ns']-g1) if back else None,states=[(ms(r['monotonic_ns']-g0),state(r),r['transport']['position'],r['transport']['playing']) for r in near if 'transport'in r])
(base/(name+'-mtc.json')).write_text(json.dumps(info,indent=2))
print(json.dumps(info,ensure_ascii=False)[:1100])
