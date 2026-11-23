from pathlib import Path
from analyse import np,pcm
import json,sys
base=Path(__file__).resolve().parent
def get(label):
 f=next((base/label).glob('*/*_TR02.wav'))
 return pcm(f)
ref=get('take1')
at=round(5.0135*48000)
template=ref[at:at+3600]
T=len(template)
out={}
for label in sys.argv[1:]:
 y=get(label)
 a=round(4.6*48000);b=round(5.42*48000);samples=y[a:b]
 # Cross-check against the same attack waveform, using normalized correlation.
 prod=np.correlate(samples,template,mode='valid')
 sq=np.r_[0.,np.cumsum(samples*samples)]
 score=prod/np.sqrt(np.maximum(sq[T:]-sq[:-T],1e-20)*np.dot(template,template))
 i=int(np.argmax(score));idx=a+i
 rms=json.loads((base/(label+'-audio.json')).read_text())['anchor']
 out[label]=dict(rms_ms=rms['signed_offset_ms'],template_ms=round((idx-240000)/48,3),match=round(float(score[i]),5),position_samples=idx)
print(json.dumps(out,indent=2))
(base/'anchor-crosscheck.json').write_text(json.dumps(out,indent=2))
