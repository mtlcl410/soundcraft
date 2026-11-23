from partition import *
import subprocess,threading,time
sys.path.insert(0,str(d.parent))
from desktop_sync import cmd
p=json.loads((d/'control.json').read_text())['port']
base=d/sys.argv[1];base.mkdir(exist_ok=False)
events=[]
def launch(name,args):
 with (base/(name+'.log')).open('wb') as log: return subprocess.Popen(args,cwd=d,stdout=log,stderr=subprocess.STDOUT)
flag=base/'end.flag'
wire_tap=launch('wire',[str(d/'tap.exe'),str(base/'ready'),str(flag),str(base/'wire.csv')])
render=launch('render',[str(d/'phase-audio.exe'),'loop',str(base/'loop'),str(flag)])
def sample():
 with (base/'lead.jsonl').open('w',buffering=1) as f:
  while not flag.exists():
   r={'qpc':time.perf_counter()}
   try:
    s=cmd(p,'setup.midi_sync_status');r.update(lead=s['output']['reported_lead_us'],clamps=s['output']['lead_clamps'],state=s['mtc_chase']['state'])
   except Exception as exc:r['error']=str(exc)
   f.write(json.dumps(r)+'\n');time.sleep(.12)
sampler=threading.Thread(target=sample);sampler.start()
try:
 for i in range(80):
  if (base/'ready').exists() and (base/'loop.csv').exists():break
  if render.poll() is not None or wire_tap.poll() is not None:raise RuntimeError('Capture failed to start')
  time.sleep(.1)
 else:raise RuntimeError('Could not open audio and MIDI endpoints')
 for action in sys.argv[2:]:
  assert not cmd(p,'transport.status')['playing']
  if action=='reopen':
   cfg=cmd(p,'ui.audio_device')['config']
   assert cfg['output'] is None
   print('Reapply current output',cmd(p,'ui.audio_device',output=None)['device'],flush=True);time.sleep(1.5)
  else:
   prior_locks=cmd(p,'setup.midi_sync_status')['mtc_chase']['locks']
   t=time.perf_counter()
   subprocess.run([sys.executable,'-X','utf8',str(d/'replay-reference.py')],check=True)
   assert cmd(p,'setup.midi_sync_status')['mtc_chase']['locks']>prior_locks,'No lock on physical MIDI replay'
   events.append({'action':action,'start':t,'stop':time.perf_counter()})
   print(action,'complete',flush=True)
  assert render.poll() is None and wire_tap.poll() is None
finally:
 flag.touch();sampler.join();print('capture return codes',wire_tap.wait(timeout=12),render.wait(timeout=12))
 (base/'actions.json').write_text(json.dumps(events,indent=2))
runs=wire(base);assert len(runs)==len(events),(len(runs),len(events))
a=Audio(base/'loop'); obs=[json.loads(x) for x in (base/'lead.jsonl').read_text().splitlines()]
for event,(z,sc,count,frame) in zip(events,runs):
 assert event['start']<z+5<event['stop']
 v=[s for s in obs if z+3<s['qpc']<z+6 and 'lead'in s];assert v
 found=[m for ch in range(2) if (m:=a.find(z+5,ch,ref))]
 t,cc=max(found,key=lambda m:abs(m[1]),default=(0,0))
 event.update(render_ms=round((t-z-5)*1000,3) if abs(cc)>.9 else None,score=round(cc,5),lead_range_us=[min(r['lead'] for r in v),max(r['lead'] for r in v)],clamp_delta=v[-1]['clamps']-v[0]['clamps'])
print(json.dumps(events,indent=2))
(base/'result.json').write_text(json.dumps(events,indent=2))
