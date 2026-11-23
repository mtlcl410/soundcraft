"""Verify the first audible VST3 call, physical MIDI sequence and MAIN recordings."""
from pathlib import Path
import json,sys
w=Path(__file__).resolve().parent
d=w.parent;f=d/'waveform-followup'
sys.path[:0]=[str(f),str(d)]
cases=sys.argv[1:]
assert cases
from analysis_audio import np,stereo,read
results={}
for name in cases:
 case=d/name;a=np.fromfile(case/'profile.bin','<u8').reshape(-1,8)
 j=read(case/'exact-a.json');b=j['out']['size']
 x=stereo(case/'exact-a-out.wav');idx=int(np.flatnonzero(abs(x).max(1)>12)[0])//b
 t=j['out']['ns'][idx]+sum(v[1] for v in j['anchors'])//2
 i=np.searchsorted(a[:,1],t);v=[int(z) for z in a[i]]
 assert t<=v[1]<t+2_000_000 and v[7]&4095==b and v[4]&255==1
 results[name]=dict(samples=b,deadline_ms=b*1000/44100,first_plugin_ms=(v[7]>>12)/1e6,first_callback_ms=v[2]/1e6,activation_ms=(v[4]>>8)/1e6,sha256_project=read(case/'control.json')['project_sha256'])
 print(name,results[name],flush=True)
out=w/('timing-'+cases[0]+'.json');out.write_text(json.dumps(results,indent=2))
assert all(r['first_plugin_ms'] < r['deadline_ms'] for r in results.values()),'first plug-in process exceeded ASIO buffer duration'

