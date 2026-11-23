from partition import *
def times(rows):
 points={}
 for i in range(7,len(rows)):
  p=np.array([b for t,b in rows[i-7:i+1]])
  if list(p>>4)!=list(range(8)):continue
  n=p&15
  f=(n[6]+16*(n[7]&1))*108000+(n[4]+16*n[5])*1800+(n[2]+16*n[3])*30+n[0]+16*n[1]
  if 120<=f<=180:points[int(f)]=rows[i-7][0]
 return points
out={}
for tag in ['take1','take2r','take3r','repeat01']:
 path=(d if tag=='repeat01' else old)/(tag+'-wire.jsonl')
 streams={}
 for ln in path.read_text().splitlines():
  t,port,b=json.loads(ln)
  if b[0]==241:streams.setdefault(port,[]).append((t,b[1]))
 a=next((times(v) for k,v in streams.items() if k.startswith('UM-ONE')),{})
 b=next((times(v) for k,v in streams.items() if k.startswith('Model 12')),{})
 dt=[(a[i]-b[i])/1e6 for i in set(a)&set(b)]
 out[tag]=dict(paired_groups=len(dt),din_minus_model_usb_ms=[round(float(v),3) for v in np.percentile(dt,[5,50,95])] if dt else None)
print(json.dumps(out,indent=2))
(d/'two-midi-paths.json').write_text(json.dumps(out,indent=2))
