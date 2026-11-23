from pathlib import Path
from analyse import pcm,np
import json
d=Path(__file__).resolve().parent
src=d.parent/'h-mtc-sd-20261121-211205'
ref=pcm(next((src/'take1').glob('*/*_TR02.wav')))[240648:244248].copy()
out={}
for tag in ['take1','take2','take3','take2r','take3r']:
 f=next((src/tag).glob('*/*_TR12.wav'))
 y=pcm(f)[220800:260160]
 prod=np.correlate(y,ref,mode='valid')
 sq=np.r_[0.,np.cumsum(y*y)]
 score=prod/np.sqrt(np.maximum(sq[len(ref):]-sq[:-len(ref)],1e-20)*np.dot(ref,ref))
 i=int(score.argmax())
 out[tag]={'file':f.name,'onset_ms':round((i+220800-240000)/48,3),'coefficient':round(float(score[i]),5)}
print(json.dumps(out,indent=2))
(d/'main-anchors.json').write_text(json.dumps(out,indent=2))
