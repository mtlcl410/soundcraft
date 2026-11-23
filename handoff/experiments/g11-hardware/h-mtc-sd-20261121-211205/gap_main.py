from pathlib import Path
import json,wave,sys
from analyse import pcm,np,db
ev=Path(__file__).resolve().parent
def tr2(label): return next((ev/label).glob('*/*_TR11.wav'))
def extract(target,start,stop,out):
 with wave.open(str(target),'rb') as w:
  w.setpos(round(start*48000))
  data=w.readframes(round((stop-start)*48000))
  with wave.open(str(out),'wb') as dst:
   dst.setparams(w.getparams())
   dst.writeframes(data)
project=json.loads((ev/'smu-model12-chase.scraft').read_text())
notes=project['tracks'][0]['playlists'][0]['clips'][0]['content']['Midi']['sequence']['notes']
c=json.loads((ev/'take3-mtc.json').read_text())['cable']
lo=max(0,int(c['last_qf_elapsed_s'])-2)
hi=min(65,int(c['first_qf_back_elapsed_s'])+4)
out={}
for label in ['take1','take3']:
 f=tr2(label)
 y=pcm(f)
 rows=[]
 for n in notes:
  t=n['start']/1920
  if not lo<=t<=hi:continue
  a=int(t*48000); win=y[a:a+int(.35*48000)]
  rows.append(dict(expected_s=t,midi=n['pitch'],rms_dbfs=db(np.sqrt(np.mean(win*win))),peak_dbfs=db(abs(win).max())))
 out[label]=rows
 extract(f,lo,hi,ev/(label+'-main-relock-listen.wav'))
out['clip_song_interval_s']=[lo,hi]
(ev/'gap-main-comparison.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))

