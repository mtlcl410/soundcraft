import hashlib,json,os,pathlib,socket,subprocess,sys,time
here=pathlib.Path(__file__).resolve().parent
base=here.parent
sys.path.insert(0,str(base))
from desktop_sync import cmd
exe=base.parent/'r4-hardware-0a8f553'/'soundcraft.exe'
digest=hashlib.file_digest(exe.open('rb'),'sha256').hexdigest()
if not digest.startswith('f02d245a') or not digest.endswith('def88f83'):raise RuntimeError(digest)
d=json.loads((base/'smu-model12-chase.scraft').read_text())
d['name']='Back to the Chorus - 120 BPM'
t=d['tracks'][0];t['name']='S-MU2000 - bass and kit';t['mixer']['volume_db']=-9
c=t['playlists'][0]['clips'][0];c['name']='Verse 1-4 / Chorus 5-8';c['length']=768000
notes=[]
def note(beat,pitch,channel,velocity,length):
 notes.append(dict(start=round(beat*960),pitch=pitch,channel=channel,velocity=velocity,length=round(length*960),release_velocity=64))
for bar,root in enumerate([36,33,29,31,36,29,33,31]):
 for beat in ([0,2] if bar<4 else [0,1.5,2,3.5]):
  # Leave the first eighth of the chorus completely clear for its unique crash.
  offset=0.5 if (bar==4 and beat==0) else 0
  note(4*bar+beat+offset,root if beat<2 else root+7,0,76,0.35)
 if bar>=4:
  for beat in [0,1,2,3]:
   if bar==4 and beat==0:continue
   note(4*bar+beat,36 if beat%2==0 else 38,9,68,0.12)
  for beat in [0.5,1.5,2.5,3.5]:note(4*bar+beat,42,9,50,0.10)
note(16,49,9,111,0.40)
c['content']['Midi']['sequence']={'notes':sorted(notes,key=lambda n:n['start']),'ctrls':[]}
d['markers']=[dict(id=i,number=i-2,name=label,kind='Marker',start=pos,end=pos,comments='',color=None,ruler=1,track=None) for i,label,pos in [(3,'Verse',0),(4,'Chorus - crash',384000)]]
d['next_id']=5
song=here/'Back to the Chorus.scraft';song.write_text(json.dumps(d,ensure_ascii=False),encoding='utf8')
with socket.socket() as sock:sock.bind(('127.0.0.1',0));p=sock.getsockname()[1]
cfg=here/'private-settings';cfg.mkdir(exist_ok=True)
env=dict(os.environ,SOUNDCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(cfg),VST3_PATH='E:/S-MU2000-windows-x64/plugins',CLAP_PATH='E:/S-MU2000-windows-x64/plugins',S_MU2000_ROMS='E:/S-MU2000-windows-x64/roms')
with (here/'desktop.log').open('wb') as log:
 proc=subprocess.Popen([str(exe),'--control',str(p),str(song)],cwd=here,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,startupinfo=(lambda s:(setattr(s,'dwFlags',subprocess.STARTF_USESHOWWINDOW),setattr(s,'wShowWindow',0),s)[2])(subprocess.STARTUPINFO()))
(here/'control.json').write_text(json.dumps(dict(port=p,pid=proc.pid,exe=str(exe),sha256=digest)))
for _ in range(100):
 try:cmd(p,'transport.status');break
 except Exception:
  if proc.poll()!=None:raise RuntimeError((here/'desktop.log').read_text())
  time.sleep(.3)
out=next(a['name'] for h in cmd(p,'ui.audio_device',list=True)['systems'] if h['is_default'] for a in h['outputs'] if 'Model 12' in a['name'])
print(cmd(p,'ui.audio_device',output=out,buffer_size=480,sample_rate=48000))
print(cmd(p,'transport.status')); print(cmd(p,'track.list'))
