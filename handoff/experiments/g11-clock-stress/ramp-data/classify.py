import math
from pathlib import Path
from collections import deque
def est(stamps):
 t=stamps
 n=len(t)//3
 if n<8:return 0,0,0
 data=t[-3*n:];means=[sum(data[i*n:(i+1)*n])/n for i in range(3)];c=means[2]-2*means[1]+means[0];P=(means[2]-means[0])/(2*n)
 x=(len(t)-1)/2; m=sum((i-x)*(y-t[-1]) for i,y in enumerate(t))/(len(t)*(len(t)**2-1)/12);b=sum(t)/len(t);noise=math.sqrt(sum((y-(b+(i-x)*m))**2 for i,y in enumerate(t))/len(t))
 return abs(c)/(noise*math.sqrt(6/n)+1e-5),abs(c)/((P*n)**2/1e6),n
def gen(bpm,j,delta=0,bars=16):
 stamps=[];seed=100 if delta==0 else 42
 def unit():
  nonlocal seed
  seed=(seed*6364136223846793005+1)&(2**64-1);return ((seed>>11)+1.)/((1<<53)+1.)
 t=0
 for i in range(700 if delta==0 else bars*192+1):
  if delta==0:
   stamp=round((100000+i*2_500_000./bpm+math.sqrt(-2*math.log(unit()))*math.cos(2*math.pi*unit())*j)/1000.)*1000
  else:
   unit();noise=int((seed>>32)%(2*j+1)-j) if i else 0;stamp=round(t)+noise;t+=2_500_000./(bpm+delta*(1-abs(i/(bars*96)-1)))
  stamps.append(stamp)
  yield est(stamps[-192:])
for b in (90,120,174):
 for j in (500,2000,4000):
  v=list(gen(b,j))[24:];print('steady',b,j,'maxsigma',max([0]+[s for s,a,_ in v if a>.00045]),'counts',[sum(s>k and a>.00045 for s,a,_ in v) for k in (2,3,4,5)])
for d in (0.3,9.92,-9.92):
 for j in (0,1000,2000):
  v=list(gen(124,j,d,16 if d==0.3 else 32));print('ramp',d,j,'first',next((i for i,(s,a,_) in enumerate(v) if s>4 and a>.00045),None),'counts',[sum(s>k and a>.00045 for s,a,_ in v) for k in (2,3,4,5)])
