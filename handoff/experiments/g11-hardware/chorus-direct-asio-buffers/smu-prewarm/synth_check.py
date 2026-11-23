"""Offline, deterministic note from the actual project's saved instrument state."""
import base64,struct,json,wave,subprocess,sys,os,hashlib
from pathlib import Path
w=Path(__file__).parent; d=w.parent
state=base64.b64decode(json.loads((d.parent/'chorus-direct-asio/session/Back to the Chorus.scraft').read_bytes())['tracks'][0]['instrument']['state'])
assert state[:4]==b'SCV3'; n=int.from_bytes(state[4:8],'little');assert 12<n<=len(state)-8
(w/'project-component.bin').write_bytes(state[8:8+n])
track=bytes.fromhex('00902d60 60802d00 00903450 60803400 00ff2f00')
(w/'bass.mid').write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,96)+b'MTrk'+struct.pack('>I',len(track))+track)
dll=sys.argv[1];tag=sys.argv[2];dest=w/(tag+'-bass.wav')
with (w/(tag+'-synth.log')).open('wb') as log:
 subprocess.run(['E:/S-MU2000-windows-x64/bin/vst3probe.exe',dll,str(w/'bass.mid'),str(dest),'--state',str(w/'project-component.bin'),'--rate','48000','--block','70','--tail','0.15'],stdout=log,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,S_MU2000_ROMS='E:/S-MU2000-windows-x64/roms'))
with wave.open(str(dest)) as wav: raw=wav.readframes(wav.getnframes())
assert max(raw)>0 and len(raw)>96000
print(tag,len(raw),hashlib.sha256(raw).hexdigest())

