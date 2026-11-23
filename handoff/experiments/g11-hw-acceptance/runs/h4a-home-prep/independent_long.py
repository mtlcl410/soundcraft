from pathlib import Path
import json,os,subprocess,sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'audio'))
from m1 import np,read_blocks
out=Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN'])
t=np.arange(24000,48000*110,24000)
raw=np.zeros(48000*110,dtype='<i2')
rng=np.random.default_rng(1663)
for i in t:raw[i:i+127]=rng.choice([-1024,1024],127)
raw.tofile(out/'markers.raw')
cap=out/'driver';cap.mkdir()
subprocess.run([str(root/'audio/build/independent.exe'),'48000','256',str(out/'markers.raw')],env=os.environ|{'SC_ASIO_EVIDENCE':str(cap),'SC_ASIO_RETURN_INDEX':'8'},timeout=135,check=True)
meta,pcm,blocks=read_blocks(cap)
dev=dict(device='Model Mixer ASIO',sample_rate=meta['sample_rate'],buffer_frames=meta['buffer'])
assert (dev['sample_rate'],dev['buffer_frames'],meta['input_index'])==(48000,256,8)
for f in ('device-start.json','device-end.json'):(out/f).write_text(json.dumps(dev))
x,y=pcm.T
ix=np.where(abs(x)>1e-5)[0];starts=ix[np.r_[True,np.diff(ix)>3000]]
assert len(t)==len(starts) and np.array_equal(np.diff(t),np.diff(starts))
rows=[]
for i in starts:
    ref=x[i:i+127].astype(float);samples=y[i:i+8192].astype(float)
    corr=np.correlate(samples,ref,mode='valid')
    k=int(np.argmax(np.abs(corr))); score=float(abs(corr[k])/max(1e-18,np.linalg.norm(ref)*np.linalg.norm(samples[k:k+127])))
    rows.append([int(i),k,score])
assert min(r[2] for r in rows)>.85
delay=[r[1] for r in rows]
doc=dict(markers=len(rows),minimum=min(delay),maximum=max(delay),peak_to_peak_samples=max(delay)-min(delay),changes=[[j,delay[j-1],delay[j]] for j in range(1,len(delay)) if delay[j]!=delay[j-1]],min_score=min(r[2] for r in rows),max_callback_ms=float(np.diff(blocks['qpc']).max()/meta['qpc_frequency']*1000),rows=rows)
(out/'long-return.json').write_text(json.dumps(doc,indent=2))
print({k:v for k,v in doc.items() if k!='rows'})

