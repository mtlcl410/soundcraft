import pathlib,sys,time,wave,json
here=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(here.parent/'capture-deps'))
import pyaudiowpatch as pa,numpy as np
a=pa.PyAudio();h=a.get_host_api_info_by_type(pa.paWASAPI);dev=next(d for d in a.get_device_info_generator() if d['hostApi']==h['index'] and 'Model 12' in d['name'] and d['maxOutputChannels'])
with wave.open(str(here/'reference.wav')) as w:
 fr=json.loads((here/'reference-analysis.json').read_text())['crash_recording_frames'][0]
 w.setpos(fr-96000); data=w.readframes(48_000*5)
stream=a.open(format=pa.paInt16,rate=48000,channels=2,output=True,output_device_index=dev['index'])
try:
 print('READY',flush=True);time.sleep(4)
 for i in range(2):stream.write(data);stream.write(bytes(48000*2))
finally:stream.stop_stream();stream.close();a.terminate()
print('SENT',flush=True)
