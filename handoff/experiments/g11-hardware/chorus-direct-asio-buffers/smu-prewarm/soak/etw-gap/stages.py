from pathlib import Path
import sys,json,csv,collections,bisect
tag=sys.argv[1]; dec=Path('decoded-'+tag)
read=lambda f:json.loads(Path(f).read_text(encoding='utf-8-sig'))
p=read(f'partition-{tag}.json');g=read(f'gaps-{tag}.json');tid=p['tid']
matches=[];events=[]
for t,c,o,n,st,reason in csv.reader(open(dec/'switch.csv')):
    if int(o)==tid: events.append((int(t),'Wait' if st=='Wait' else 'Ready' if st in ('Ready','DeferredReady','Standby') else 'Unknown',int(c),reason))
    if int(n)==tid: events.append((int(t),'Run',int(c),''))
for t,n,w,c in csv.reader(open(dec/'ready.csv')):
    if int(n)==tid:events.append((int(t),'Ready',int(c),'ready'))
events.sort(key=lambda e:e[0]);et=[e[0] for e in events]
irqs=[]
for end,c,ms,addr,kind in csv.reader(open(dec/'irq.csv')):
    r=int(end);irqs.append((r-round(float(ms)*1e6),r,int(c),addr,kind))
def amount(lo,hi):
    a=bisect.bisect_right(et,lo)-1; r=bisect.bisect_right(et,hi)
    rec=events[a:r];sp=collections.Counter();on=[];trans=[]
    for i,(t,state,c,why) in enumerate(rec):
        start=max(lo,t);end=rec[i+1][0] if i+1<len(rec) else hi
        if end>start:
            sp[state]+=end-start
            if state=='Run':on.append((start,end,c))
        if lo<=t<=hi:trans.append(dict(at_ms=round((t-lo)/1e6,4),state=state,cpu=c,reason=why))
    onirq=[(min(r,e)-max(l,s),c,k,addr) for l,r,c,addr,k in irqs for s,e,core in on if c==core and l<e and r>s]
    return {k:round(v/1e6,4) for k,v in sp.items()},trans,(round(max(z[0] for z in onirq)/1e6,4) if onirq else 0)
for serial,lo,hi,delta in g['rows']:
    sp,trans,irq=amount(lo,hi);assert abs(sum(sp.values())-delta)<.001
    matches.append(dict(serial=serial,ms=delta,initial_state=events[bisect.bisect_right(et,lo)-1][1],stages=sp,transitions=trans,largest_same_cpu_irq_during_run_ms=irq))
Path(f'stages-{tag}.json').write_text(json.dumps(matches,indent=2));print(matches[0])


