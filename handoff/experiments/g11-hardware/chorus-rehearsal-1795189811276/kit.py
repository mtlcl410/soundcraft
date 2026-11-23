import json,pathlib,struct,subprocess,wave,sys,time
here=pathlib.Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent),str(here.parent/'capture-deps')]
from desktop_sync import cmd
import numpy as np
p=json.loads((here/'control.json').read_text())['port']
def c(k,**v):return cmd(p,k,**v)
def vlq(n):
 a=[n&127]
 while n>127:n>>=7;a.append(128|(n&127))
 return bytes(reversed(a))
voices=[(49,'Crash'),(36,'Kick'),(38,'Snare'),(42,'Hat')]
tr=bytearray(b'\x00\xff\x51\x03\x07\xa1\x20')
for i,(n,name) in enumerate(voices):
 tr.extend(vlq(960 if i==0 else 3720)+bytes([0x99,n,104])+vlq(120)+bytes([0x89,n,0]))
tr.extend(b'\x00\xff\x2f\x00')
mid=here/'drum-audition.mid';mid.write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,960)+b'MTrk'+struct.pack('>I',len(tr))+tr)
inst=pathlib.Path('E:/S-MU2000-windows-x64')
wav=here/'drum-audition.wav'
if not wav.exists():
 with (here/'render.log').open('wb') as log:subprocess.run([inst/'bin/render.exe',inst/'roms',mid,wav,'9','--reset','xg','--sample-rate','48000','--fast-midi'],stdout=log,stderr=log,check=True)
with wave.open(str(wav)) as w:
 rate=w.getframerate();ch=w.getnchannels();x=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,ch)
power=np.max(np.abs(x.astype(float)),axis=1)
first=np.where(power>30)[0][0]
print('first',first,'rate',rate,flush=True)
song=here/'Back to the Chorus.scraft'
d=json.loads(song.read_text());seq=d['tracks'][0]['playlists'][0]['clips'][0]['content']['Midi']['sequence'];drums=[n for n in seq['notes'] if n['channel']==9];seq['notes']=[n for n in seq['notes'] if n['channel']==0];d['tracks'][0]['name']='S-MU2000 - verse bass';song.write_text(json.dumps(d),encoding='utf8')
c('session.open',path=str(song))
for i,(pitch,name) in enumerate(voices):
 lo=max(0,first+i*2*rate-2400);sl=x[lo:lo+int(1.8*rate)];lvl=np.max(abs(sl.astype(float)),axis=1)
 ix=int(np.flatnonzero(lvl>max(30,lvl.max()*.012))[0]);sl=sl[ix:]
 file=here/(name+'.wav')
 with wave.open(str(file),'wb') as w:w.setparams((ch,2,rate,0,'NONE',''));w.writeframes(sl.tobytes())
 track=c('track.new',kind='instrument',format='stereo',instrument='sampler',name='S-MU2000 '+name)['tracks'][0]
 print(c('mix.sampler_load',track=track,path=str(file),params={'root_note':60,'attack':0}),flush=True)
 clip=c('midi.new_clip',track=track,start=0,end=768000)['clip']
 for n in drums:
  if n['pitch']==pitch:c('midi.note_add',clip=clip,pitch=60,velocity=n['velocity'],channel=0,start_ticks=n['start'],length_ticks=1200 if name=='Crash' else 240)
c('session.save',path=str(song))
print(c('session.inspect')['name'] if 'name' in c('session.inspect') else 'saved',flush=True)
