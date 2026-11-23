from pathlib import Path
import sys,json,numpy as np
case=Path(sys.argv[1]).resolve(); E={'__file__':str(case/'sd-landmarks.py')}
exec(compile((case/'sd-landmarks.py').read_text(encoding='utf-8-sig').split('res={}')[0],E['__file__'],'exec'),E)
fetch=E['fetch']; usb,out=E['usb'],E['out']; r=44100
from audio import gain
def rms(x):return float(np.sqrt(np.mean(x*x)))
q=json.loads((case/'four-paths.json').read_bytes()); result=[]
for z in q['paths'][0]['offset_changes']:
 left=z['before']['out_frame']; n=z['after']['out_frame']-left
 lag=z['before']['usb_minus_out'];delta=z['delta']['usb_minus_out']
 if delta==0:continue
 u=fetch(usb,left+lag,n).astype(float)*32768
 pre=fetch(out,left,n).astype(float)@gain*32768
 post=fetch(out,left-delta,n).astype(float)@gain*32768
 def pref(x):return np.r_[0.,np.cumsum((x*x).sum(1))]
 a=pref(u-pre);b=pref(u-post)
 guard=max(0,delta)
 idx=np.arange(1024,n-1024);loss=a[idx]+b[-1]-b[idx+guard]
 k=int(idx[loss.argmin()]);dot=(left+k)/r
 result.append(dict(seconds=dot,delta=delta,usb_frame=left+lag+k,out_frame=left+k,model='two fixed lags, no penalty inside positive step',preceding=rms(u[k-64:k]),following=rms(u[k+guard:k+guard+64]),gap_rms=rms(u[k:k+guard]) if guard else None,gap_peak=float(np.max(abs(u[k:k+guard]))) if guard else None,fit_error_before=rms(u[k-1024:k]-pre[k-1024:k]),fit_error_after=rms(u[k+guard:k+guard+1024]-post[k+guard:k+guard+1024]),route_delta=z['delta']))
(case/'transition-fit.json').write_text(json.dumps(result,indent=2))
for x in result:print({k:x[k] for k in ('seconds','delta','preceding','following','gap_rms','gap_peak','fit_error_before','fit_error_after')})

