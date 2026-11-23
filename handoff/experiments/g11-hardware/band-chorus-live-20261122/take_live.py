import json,pathlib,sys,time,threading,wave,collections
here=pathlib.Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent),str(here.parent/'capture-deps')]
from desktop_sync import cmd
import pyaudiowpatch as pa,rtmidi,numpy as np
mode=sys.argv[1]
p=json.loads((here/'control.json').read_text())['port']
def c(k,**v):return cmd(p,k,**v)
if c('transport.status')['playing']:raise ValueError('Stop before arming')
if mode=='monitor-reference':c('setup.midi_clock_follow',enabled=False)
else:c('setup.midi_clock_follow',input='UM-ONE',enabled=True,loss_policy='coast')
audio=pa.PyAudio()
dev=next(d for d in audio.get_loopback_device_info_generator() if 'S/PDIF' in d['name'])
channels=dev['maxInputChannels'];rate=int(dev['defaultSampleRate'])
assert rate==48000
ring=collections.deque(maxlen=100);blocks=[];states=[];midi=[];ports=[];lock=threading.Lock();active=False
def pcm(data,n,meta,flags):
 item=(time.perf_counter(),n,dict(meta),int(flags),data)
 with lock:(blocks if active else ring).append(item)
 return None,pa.paContinue
stream=audio.open(format=pa.paInt16,channels=channels,rate=rate,input=True,input_device_index=dev['index'],frames_per_buffer=480,stream_callback=pcm)
for i,name in enumerate(rtmidi.MidiIn().get_ports()):
 if name.startswith(('UM-ONE ','Model 12 MIDI ')):
  m=rtmidi.MidiIn();m.ignore_types(sysex=True,timing=False,active_sense=True)
  try:
   m.open_port(i);m.set_callback(lambda ev,n: midi.append([time.perf_counter(),n,list(ev[0])]) if ev[0] and ev[0][0] in (248,250,251,252,242) else None,name);ports.append(m)
  except Exception as ex:print(str(ex),flush=True)
(here/'route-take.txt').write_text(mode); print('READY',mode,dev['name'].encode('ascii','replace'),c('setup.midi_clock_follow'),flush=True)
begin=ended=None;armed=time.monotonic();last_report=0
try:
 time.sleep(.7)
 if mode=='monitor-reference':c('transport.play',**{'from':0})
 while time.monotonic()-armed < 900:
  now=time.perf_counter();tr=c('transport.status');f=c('setup.midi_clock_follow')
  if not states or tr!=states[-1][1] or f.get('state')!=states[-1][2].get('state'):states.append([now,tr,f])
  if now-last_report>0.35:
   ob=[e for e in midi if e[2][0]!=248][-12:]; (here/(mode+'-live.json')).write_text(json.dumps(dict(status=tr,follow=f,wire=ob,ports=[m.get_port_count() for m in ports]))); last_report=now
  if tr['playing'] and begin is None:
   with lock:blocks.extend(ring);active=True
   begin=now
  if mode=='monitor-reference' and begin and not ended and now-begin>12:c('transport.stop')
  if begin and not tr['playing'] and ended is None:ended=now
  if ended and now-ended>1.4:break
  time.sleep(.025)
finally:
 (here/'route-take.txt').unlink(missing_ok=True); stream.close();audio.terminate()
 for m in ports:m.close_port()
 with wave.open(str(here/(mode+'.wav')),'wb') as w:w.setparams((channels,2,rate,0,'NONE',''));w.writeframes(b''.join(b[4] for b in blocks))
 info=dict(rate=rate,channels=channels,begin=begin,end=ended,blocks=[b[:4] for b in blocks],states=states,midi=midi)
 (here/(mode+'.json')).write_text(json.dumps(info))
 print('END',begin,ended,'blocks',len(blocks),'peak',max((int(np.max(np.abs(np.frombuffer(b[4],dtype='<i2').astype('i4')))) for b in blocks if b[4]),default=0),flush=True)



