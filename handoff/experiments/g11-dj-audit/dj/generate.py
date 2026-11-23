"""Create deterministic ideal clock stimuli. All timestamps are rounded ONCE to microseconds."""
from pathlib import Path
import math
D=Path(__file__).resolve().parent
cases={}
def emit(name,base,cut,n,dt,end='natural',coast=True):
    now=0.; times=[]
    for i in range(n+1):
        times.append(round(now*1e6)); now+=dt(i,now)
    cases[name]=(base,cut,end,int(coast),times)
def period(b):return 2.5/b
def next_boundary(start,quarter_integral):
    lo,hi=0.,.55
    for _ in range(44):
        d=(lo+hi)/2
        if quarter_integral(start,d) < 2.5:lo=d
        else:hi=d
    return (lo+hi)/2
for pct in (2,3.5,5):
 for sign in (-1,1):
  for secs in (.5,1,2):
   base=128.; cut=384; t0=cut*period(base); changed=base*(1+sign*pct/100)
   def dt(i,t):
       return next_boundary(t,lambda a,d: base*d+(changed-base)*max(0,min(a+d,t0+secs)-max(a,t0)))
   emit(f'nudge_{sign*pct:+g}pct_{secs:g}s',base,cut,cut+300,dt)
for a,b in ((174,87),(87,174),(140,70),(70,140),(120,60),(60,120)):
 for cut in (384,396):
  emit(f'ratio_{a}_{b}_{cut}',a,cut,cut+192,lambda i,t:period(a if i<cut else b))
for pct in (7.9,8.0,8.1):
 for sign in (-1,1):
  for trial in range(10):
   cut=384+trial
   emit(f'edge_{sign*pct:+.1f}pct_{trial:02}',128.,cut,cut+192,lambda i,t:period(128 if i<cut else 128*(1+sign*pct/100)))
for pct in (.5,1):
 for hz in (.5,2):
  cut=384;t0=cut*period(128);w=2*math.pi*hz
  def dt(i,t):
    if i<cut:return period(128)
    return next_boundary(t,lambda a,d: 128*(d+pct/100*(math.cos(w*(a-t0))-math.cos(w*(a+d-t0)))/w))
  emit(f'wobble_{pct:g}pct_{hz:g}Hz',128,cut,cut+768,dt)
# exact time for constant BPM slope per musical beat
def line(a,b,k,n):
    slope=(b-a)/n
    return 2.5*math.log((a+slope*(k+1))/(a+slope*k))/slope
cut=384
emit('sprint_128_160_drop128',128,cut,cut+768+192,lambda i,t:line(128,160,i-cut,768) if cut<=i<cut+768 else period(128))
# Explicit accelerating curve over 32 beats; the tempo's slope doubles with elapsed beats.
def convex_interval(k):
    n=768; base=128; delta=32
    return 2.5*n/math.sqrt(base*delta)*(math.atan((k+1)*math.sqrt(delta/base)/n)-math.atan(k*math.sqrt(delta/base)/n))
emit('sprint_convex_128_160_drop128',128,cut,cut+768+192,lambda i,t:convex_interval(i-cut) if cut<=i<cut+768 else period(128))
for beats in (1,2):
 for ending in ('stop','silent','rise'):
  for coast in (False,True):
   # Tempo changes at each F8, exactly 5 BPM for final interval; resolves intended 500 ms gap.
   n=beats*24
   emit(f'brake_{beats}b_{ending}_'+('coast' if coast else 'stoploss'),128,cut,cut+n+(192 if ending=='rise' else 0),lambda i,t:period(128+(5-128)*(i-cut+1)/n) if cut<=i<cut+n else period(128),ending,coast)
levels=[120]
while levels[-1]<132:levels.append(min(132,levels[-1]*1.01))
while levels[-1]>120:levels.append(max(120,levels[-1]*.99))
emit('stair_120_132_120',120,cut,cut+24*(len(levels)-1)+192,lambda i,t:period(levels[min((i-cut)//24+1,len(levels)-1)] if i>=cut else 120))
with (D/'stimulus.tsv').open('w') as h:
 for k,(b,c,e,p,times) in cases.items():
    h.write('\t'.join(map(str,(k,b,c,e,p,','.join(map(str,times)))))+'\n')
print('cases',len(cases))
