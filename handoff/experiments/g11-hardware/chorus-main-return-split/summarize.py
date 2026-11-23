"""Recalculate stage means and audit transport, recorded signal and FIFO health per take."""
from pathlib import Path
import json, statistics as st
from assess import np
from assess import mono,matches
d=Path(__file__).resolve().parent
def read(path):return json.loads(path.read_text())
baseline=read(d.parent/'chorus-dispatch-release'/'final-acceptance.json')
trace=read(d.parent/'chorus-dispatch-final'/'final-acceptance.json')
current=read(d/'final-acceptance.json')
cal=read(d/'asio-control.json')
assert read(d/'control.json')['sha256']==read(d.parent/'chorus-dispatch-release'/'control.json')['sha256']
assert read(d/'control.json')['project_sha256']==read(d.parent/'chorus-dispatch-release'/'control.json')['project_sha256']
def group(rows):
    exact=[v for v in rows if v['spp']==64]
    return {k:dict(mean=st.mean(raw),minimum=min(raw),maximum=max(raw)) for k in exact[0] if k.endswith('_ms') for raw in [[v[k] for v in exact]]}
stats={'previous':group(baseline.values()),'probes':group(trace.values())}
ref=d.parent/'chorus-latency-1675-fixed'; idx=read(ref/'monitor-reference-analysis.json')['crash_recording_frames'][0]+24000
src=mono(ref/'monitor-reference.wav')[idx:idx+2400]
target=np.arange(0,len(src)-1,48000/44100)
template=np.interp(target,np.arange(len(src)),src)
for label in (20,40):
    samples={k:v for k,v in current.items() if k.startswith('queue'+str(label))}
    assert len(samples)==6
    assert sorted(v['spp'] for v in samples.values())==[64,64,64,64,65,65]
    for k,v in samples.items():
        assert all(v[s]==int(v['spp']==64) for s in ('digital_count','bridgein_count','asio_count','main_count'))
        assert v['ticks']==144
        v['main_music_match']=float(matches(mono(d/(k+'-main.wav')),template).max())
        assert v['main_music_match']>.90,(k,v['main_music_match'])
        j=read(d/(k+'.json'))
        midi=[(t,m) for t,port,m in j['midi'] if port.startswith('UM-ONE')]
        assert [m for t,m in midi if m[0]!=248]==[[242,v['spp'],0],[251],[252]]
        first=next(t for t,m in midi if m[0]==248);last=next(t for t,m in midi if m[0]==252)
        all_cb=read(d/(k+'-asio-main-times.json'))
        cb=[b for b in all_cb if first-.02<=b[0]<=last+.12]
        assert cb
        v['short_callbacks']=sum(b[5]!=b[1] for b in cb)
        v['overflow_trims']=max(b[6] for b in cb)-min(b[6] for b in cb)
        v['flagged_asio_callbacks']=sum(b[8] for b in cb)
        v['asio_block_frames']=list(sorted(set(b[1] for b in cb)))
        if v['spp']==64:assert abs(v['digital_to_main_ms']-v['taps_ms']-v['bridge_to_output_ms']-v['output_to_main_ms'])<.005
    stats[str(label)]=group(samples.values())
assert len(cal['takes'])==6
stats['calibration']=[t['callback_to_main_ms'] for t in cal['takes']]
(d/'per-take.json').write_text(json.dumps(current,indent=2));(d/'stage-summary.json').write_text(json.dumps(stats,indent=2))
for key in ('previous','40','20'):
    print(key,{k:round(v['mean'],2) for k,v in stats[key].items()})
print('calibration:',stats['calibration'],cal['flags'])
print('health:',[(k,v['short_callbacks'],v['overflow_trims'],v['flagged_asio_callbacks'],round(v['main_music_match'],3)) for k,v in current.items()])

