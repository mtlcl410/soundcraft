from pathlib import Path
import sys,json,csv,bisect
from collections import Counter,defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from timing import *
b=int(sys.argv[1]);tag=sys.argv[2] if len(sys.argv)>2 else str(b);case=root/(tag if tag.startswith('usb') else f'sched{b}');dec=Path(f'decoded-{tag}')
s=read(dec/'summary.json');g=read(Path(f'gaps-{tag}.json'))
a=load_profile(case/'profile.bin').astype(np.int64);mid=a[:,1]-a[:,2]//2
if tag.startswith('usb'):
    rec=read(case/'record.json'); wall_offset=sum(rec['anchors'])//2
    lower,upper=[next(t+wall_offset for t,m in rec['events'] if m==[status]) for status in (248,252)]
    mid=mid[(mid>=lower)&(mid<upper)]
switch=[];incoming=defaultdict(list);spans=defaultdict(list);known=set(s['threads'])
for row in csv.reader((dec/'switch.csv').open()):
 t,c,o,n=map(int,row[:4]);switch.append((t,c,o,n,*row[4:]))
 if o in known and incoming[o]:
    t0,c0=incoming[o][-1]
    if c==c0 and t0<=t:spans[o].append((t0,t,c))
 if n in known:incoming[n].append((t,c))
def covered(timeline,points):
 if not timeline:return 0
 v=np.array(timeline);i=np.searchsorted(v[:,0],points,side='right')-1
 return int(((i>=0)&(points<v[i,1])).sum())
scores=sorted([(covered(v,mid),k) for k,v in spans.items()],reverse=True)
tid=scores[0][1]
rdy=[tuple(map(int,v)) for v in csv.reader((dec/'ready.csv').open()) if int(v[1])==tid]
images=[]
for l in (dec/'images.tsv').read_text(encoding='utf-8-sig',errors='replace').splitlines():
 try:
    base,size,name=l.split('\t',2);images.append((int(base),int(base)+int(size),name.split('\\')[-1]))
 except ValueError:pass
def driver(ptr):
 return next((n for l,r,n in images if l<=ptr<r),hex(ptr))
irqs=[]
for v in csv.reader((dec/'irq.csv').open()):
 t,c=int(v[0]),int(v[1]);irqs.append((t-round(float(v[2])*1e6),t,c,driver(int(v[3])),v[4]))
us=[]
for l in (dec/'usb.tsv').open(encoding='utf-8-sig'):
 t,c,k,d=l.rstrip('\r\n').split('\t',3);us.append((int(t),int(c),k,d))
details=[]
for serial,lo,hi,delta in g['rows']:
 events=[(round((t-lo)/1e6,4),c,o,n,st,re) for t,c,o,n,st,re in switch if lo-500000<=t<=hi+500000 and tid in (o,n)]
 wakes=[(round((t-lo)/1e6,4),w,c) for t,n,w,c in rdy if lo-500000<=t<=hi+500000]
 running=[(max(l,lo),min(r,hi),c) for l,r,c in spans[tid] if l<hi and r>lo]
 def clipped(l,r):return round((min(r,hi)-max(l,lo))/1e6,4)
 irq=[(clipped(l,r),c,n,k,round((l-lo)/1e6,4)) for l,r,c,n,k in irqs if l<hi and r>lo]
 uw=Counter(k for t,c,k,d in us if lo<=t<=hi)
 details.append(dict(serial=serial,outside_ms=delta,run_ms=round(sum(r-l for l,r,c in running)/1e6,4),switch=events,ready=wakes,irq_longest=sorted(irq,reverse=True)[:8],usb=dict(uw)))
out=dict(midpoint_total=len(mid),top_threads=scores[:5],tid=tid,lost=s['lost'],details=details)
Path(f'partition-{tag}.json').write_text(json.dumps(out,indent=2))
print(scores[:3],len(mid),details[0])


