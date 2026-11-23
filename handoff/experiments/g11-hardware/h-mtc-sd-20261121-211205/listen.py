from pathlib import Path
import json,sys,time,wave
from analyse import np,pcm
here=Path(__file__).resolve().parent
import pyaudiowpatch as pa
sys.path.insert(0,str(here.parent))
from desktop_sync import cmd
port=json.loads((here/'control.json').read_text())['port']
cmd(port,'setup.mtc',online=False)
app=pa.PyAudio()
try:
 host=app.get_host_api_info_by_type(pa.paWASAPI)['index']
 outs=[app.get_device_info_by_index(i) for i in range(app.get_device_count())]
 dest=next(d for d in outs if d['hostApi']==host and 'Model 12' in d['name'] and d['maxOutputChannels']>=2 and not d.get('isLoopbackDevice',False))
 print('Output',dest['name'],flush=True)
 with wave.open(str(here/'take1-relock-listen.wav'),'rb') as w:
  assert w.getnframes()==384000
 stream=app.open(format=pa.paFloat32,channels=2,rate=48000,output=True,output_device_index=dest['index'],frames_per_buffer=960)
 try:
  for label in ['take1','take3r']:
   y=pcm(here/(label+'-relock-listen.wav')).astype('float32')
   print(label,len(y)/48000,'s',flush=True)
   for pos in range(0,len(y),960): stream.write(np.repeat(y[pos:pos+960,None],2,axis=1).tobytes())
   if label=='take1':stream.write(np.zeros((48000,2),dtype='float32').tobytes())
 finally: stream.stop_stream();stream.close()
 print('Completed both SD excerpts.',flush=True)
finally:app.terminate()

