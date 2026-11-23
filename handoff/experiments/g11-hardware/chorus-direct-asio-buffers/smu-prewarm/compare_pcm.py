"""The official VST3 probe renders two notes with the project's saved bass patch."""
import hashlib,json,wave
from pathlib import Path
w=Path(__file__).resolve().parent
out={}
for case in ('before','final'):
 with wave.open(str(w/(case+'-bass.wav')),'rb') as f:
  data=f.readframes(f.getnframes())
  out[case]=dict(channels=f.getnchannels(),rate=f.getframerate(),frames=f.getnframes(),sha256_pcm=hashlib.sha256(data).hexdigest())
 assert len(set(data))>16
(w/'bass-null-test.json').write_text(json.dumps(out,indent=2))
print(out);assert out['before']==out['final'],'instrument waveform changed'

