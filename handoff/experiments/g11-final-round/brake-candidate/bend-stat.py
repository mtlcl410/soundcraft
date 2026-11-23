import math
def wire(cut,N,kind,n,d,seed,noise):
 t=0.0;w=[];sn=seed
 for p in range(N):
  sn=(sn*6364136223846793005+1)&((1<<64)-1)
  w.append(round(t)+((sn>>32)%(noise*2+1)-noise if p else 0));phase=(p-cut+1)/max(1,n)
  bpm=(120 if p<cut else 100) if kind=='single' else (128 if p<cut else (5 if p>=cut+n else (128*(5/128)**phase if d else 128-123*phase)))
  t+=2500000/bpm
 return w
def tries(w):
 for i in range(12,len(w)):
  x=w[i-12:i+1];a=x[4]-x[0];b=x[8]-x[4];c=x[12]-x[8];g=min(b-a,c-b)
  if g<=2000 or b<=1.05*a or c<=1.05*b:continue
  largest=max(x[k+2]-2*x[k+1]+x[k] for k in range(11))
  if largest>=0.8*(c-a)/4:continue
  sl=(x[12]-x[0])/12;q=(x[12]+x[0]-2*x[6])/72;res=[x[j]-x[6]-(j-6)*(sl+(j-6)*q) for j in range(13)]
  if max(map(abs,res))*2>=g:continue
  y=[x[j+1]-x[j] for j in range(12)];avg=lambda a:sum(a)/len(a)
  grad=avg(y[-2:])-avg(y[-4:-2]);grad6=avg(y[-3:])-avg(y[-6:-3]);ov=(c-a)/8
  step=min(sum((x[j]-(x[0]+(x[k]-x[0])*j/k if j<=k else x[k]+(x[12]-x[k])*(j-k)/(12-k)))**2 for j in range(13)) for k in range(2,11))
  yield i,y,round(grad/ov,2),round(grad6/ov,2),round(step/(sum(x*x for x in res) or 1),2)
for kind in ['single','brake']:
 for n in ([0] if kind=='single' else [24,48]):
  for d in ([0] if kind=='single' else [0,1]):
   for noise in ([1000] if kind=='single' else [0,1000]):
    c=396 if kind=='single' else 192
    r=list(tries(wire(c,c+max(n,8)+8,kind,n,d,42 if kind=='single' else 341,noise)))
    print(kind,n,d,noise,[(i-c,gr,gr6,ratio) for i,y,gr,gr6,ratio in r[:4]])
    if kind=='single': print(r)
