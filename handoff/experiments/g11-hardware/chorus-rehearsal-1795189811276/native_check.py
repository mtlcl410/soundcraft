from pathlib import Path
import json, os, sys, time, wave, threading
here = Path(__file__).resolve().parent
sys.path[:0] = [str(Path(os.environ["TEMP"])/"soundcraft-chorus-pa441"), str(here.parent/"capture-deps")]
os.environ["SD_ENABLE_ASIO"] = "1"
import numpy as np
import sounddevice as sd
which = sys.argv[1]
play = "play" in sys.argv[2:]
if which == "ASIO":
    dev = next(i for i,d in enumerate(sd.query_devices()) if d["name"]=="Model Mixer ASIO")
    config = sd.AsioSettings(channel_selectors=[8,9] if "9/10" in sys.argv[2:] else [0,1])
else:
    dev = next(i for i,d in enumerate(sd.query_devices()) if sd.query_hostapis(d["hostapi"])["name"]=="Windows WASAPI" and d["max_output_channels"] and "Model 12" in d["name"])
    config = sd.WasapiSettings(exclusive=True)
rate=44100
with wave.open(str(here/"reference.wav"),"rb") as w:
    peak_frame=json.loads((here/"reference-analysis.json").read_text())["crash_recording_frames"][0]
    w.setpos(peak_frame-2*w.getframerate())
    orig=np.frombuffer(w.readframes(5*w.getframerate()),dtype="<i2").reshape(-1,2)/32768
    ix=np.arange(rate*5)*w.getframerate()/rate
    data=np.stack([np.interp(ix,np.arange(len(orig)),ch) for ch in orig.T],axis=1).astype("float32")
pos=0
goal=len(data) if play else rate
done=threading.Event()
def write(out,n,t,status):
    global pos
    out.fill(0)
    k=min(goal-pos,n)
    if play: out[:k]=data[pos:pos+k]
    pos+=k
    if pos==goal: raise sd.CallbackStop
with sd.OutputStream(device=dev,samplerate=rate,channels=2,dtype="float32",extra_settings=config,callback=write,finished_callback=done.set) as stream:
    completed=done.wait(goal/rate+2)
print(json.dumps(dict(backend=which, requested=goal, frames=pos, completed=completed, music=play)))
sys.exit(0 if completed and pos==goal else 2)