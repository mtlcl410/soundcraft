import pathlib,sys,os,time,subprocess
p=pathlib.Path(__file__).resolve();sys.path[:0]=[str(pathlib.Path(os.environ['TEMP'])/'soundcraft-chorus-pa441'),str(p.parent.parent/'capture-deps')];os.environ['SD_ENABLE_ASIO']='1'
import sounddevice as sd
device=next(i for i,d in enumerate(sd.query_devices()) if d['name']=='Model Mixer ASIO')
if len(sys.argv)>1:
 with sd.InputStream(device=device,channels=2,extra_settings=sd.AsioSettings(channel_selectors=[10,11]),samplerate=44100,blocksize=256,callback=lambda *a:None):
    time.sleep(.2);print('independent input opened')
else:
 with sd.OutputStream(device=device,channels=2,extra_settings=sd.AsioSettings(channel_selectors=[8,9]),samplerate=44100,blocksize=256,callback=lambda data,*_:data.fill(0)):
    sub=subprocess.run([sys.executable,str(p),'input'],capture_output=True,text=True,timeout=12);print(sub.returncode,sub.stdout,sub.stderr)

