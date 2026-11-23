from pathlib import Path
import numpy as np,json,sys
case=Path(sys.argv[1]).resolve();E={'__file__':str(case/'sd-landmarks.py')}
exec(compile((case/'sd-landmarks.py').read_text(encoding='utf-8-sig').split('res={}')[0],E['__file__'],'exec'),E)
out=E['out'];usb=E['usb'];buf=E['buf'];rate=44100
j=json.loads((case/'timing-summary.json').read_bytes());z=json.loads((case/'sd-landmarks.json').read_bytes())
rows={}
for c in (0,1):
 digital=E['wav'](11+c); physical=E['wav'](3+c)
 for r in j['all']['overruns']:
  serial=r['serial']; pos=int(np.searchsorted(out['serial'],serial))*buf
  arr=[]
  for k in (-2048,512):
   p=pos+k;n=1024;ref=E['fetch'](out,p,n)[:,c];w=1800
   pool=E['fetch'](usb,p-w,n+2*w)[:,c];u,sim=E['best'](pool,ref,w,w);u+=p-w
   s,sc=E['best'](digital,E['fetch'](usb,u,n)[:,c],u+z[str(c)]['base'],240)
   an,ac=E['best'](physical,digital[s:s+n],s+38,80)
   arr.append([u-p,s-u,an-s])
  rows[f'{serial}.{c}']=dict(before=arr[0],after=arr[1],delta=np.subtract(arr[1],arr[0]).tolist())
(case/'overrun-flanks.json').write_text(json.dumps(rows,indent=2))
print(rows)

