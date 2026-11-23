import json, sys, wave
from pathlib import Path
from assess import measure, mono, matches, np
here=Path(__file__).resolve().parent
name=sys.argv[1]
wire=measure(name)
ref=here.parent/'chorus-latency-1675-fixed'
origin=json.loads((ref/'monitor-reference-analysis.json').read_text())['crash_recording_frames'][0]
later=mono(ref/'monitor-reference.wav')[origin+24000:origin+26400]
def examine(file):
    with wave.open(str(file),'rb') as wav:
        rate=wav.getframerate()
    x=mono(file)
    src=mono(here/'Crash.wav')
    a=np.arange(round(200*rate/48000),round(2600*rate/48000))*48000/rate
    b=np.arange(0,2399,48000/rate)
    crash=matches(x,np.interp(a,np.arange(len(src)),src))
    ix=np.flatnonzero(crash>.90)
    groups=np.split(ix,np.flatnonzero(np.diff(ix)>.10*rate)+1) if len(ix) else []
    return dict(rate=rate,crashes=len(groups),crash_score=round(float(crash.max()),4),
        later_score=round(float(matches(x,np.interp(b,np.arange(len(later)),later)).max()),4))
summary=dict(wire=wire['wire'],digital=examine(here/(name+'.wav')),main=examine(here/(name+'-main.wav')))
(here/(name+'-result.json')).write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
