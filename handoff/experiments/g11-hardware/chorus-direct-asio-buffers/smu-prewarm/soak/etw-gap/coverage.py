"""Keep playback coverage, missing return records and phase-matched waveform evidence separate."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from timing import *
from inspect_dips import run
b=int(sys.argv[1]);tag=sys.argv[2];p=root/tag
j=read(p/'record.json');anchor=sum(j['anchors'])//2
edges=[next(t+anchor for t,m in j['events'] if m==[v]) for v in [248,252]]
out=load_wave(p/'out.bin');main=load_wave(p/'in.bin')
a=load_profile(p/'profile.bin').astype(np.int64)
v=a[slice(*np.searchsorted(a[:,1],edges))]
assert np.all(np.diff(v[:,0])==1) and np.all((v[:,7]&4095)==b)
streams={}
for key,w in [('out',out),('main',main)]:
    w=w[slice(*np.searchsorted(w['ns'],edges))];diff=np.diff(w['serial'].astype(np.int64))
    missing=[dict(previous_serial=int(w['serial'][i]),missing=int(diff[i]-1),time_s=(int(w['ns'][i])-edges[0])/1e9) for i in np.flatnonzero(diff!=1)]
    assert np.all(w['size']==b)
    streams[key]=dict(records=len(w),missing_blocks=sum(x['missing'] for x in missing),missing=missing)
audio=read(root/f'audio-{tag}.json')
# A nearby missing record may prevent a candidate from being aligned. Preserve it as unevaluable.
checks=[]
for cand in audio['sliding_dips']:
    try:
        c=run(tag,waveform={'sliding_dips':[cand]})[0]
        tests=c['neighbour_offsets']
        same=min(tests,key=lambda z:z['err'])
        supporting=[q for q in c['anchors'] if q['rms']>=10 and q['error']<max(5,q['rms']*.12)]
        past=any(q['lag']==same['shift'] and q['offset']<0 for q in supporting)
        future=any(q['lag']==same['shift'] and q['offset']>0 for q in supporting)
        if past and future and same['err']<max(5,same['pred_rms']*.12):
            verdict='locally_aligned'
        else:verdict='inspect'
        checks.append(dict(**c,verdict=verdict))
    except (AssertionError,IndexError,ValueError) as e:
        checks.append(dict(**cand,verdict='unavailable',error=repr(e)))
def sec(i):return round((int(v[i,1])-edges[0])/1e9,6)
g=v[1:,1]-v[1:,2]-v[:-1,1]
target=int(np.argmin(abs(v[:,1]-(edges[0]+486.242e9))))
output=dict(version=read(p/'control.json'),plugin_sha256=j['dll_sha256'],buf=b,seconds=(edges[1]-edges[0])/1e9,
    transport_other=[m for _,m in j['events'] if m!=[248]],clocks=sum(m==[248] for _,m in j['events']),stopped=not j['final']['playing'],
    streams=streams,callback_max_ms=float(v[:,2].max()/1e6),outside_max_ms=float(g.max()/1e6),max_gap_at=sec(int(g.argmax()+1)),
    song_486_max_outside_within_20ms=float(g[abs(v[1:,1]-(edges[0]+486242000000))<=20000000].max()/1e6),profile_count=len(v),
    overruns=int((v[:,2]>b/44100*1e9).sum()),over6099_ms=int((g>=6099000).sum()),cymbals=audio['counts_8s_pattern'],
    duration_above_silence_candidates=checks,unchecked_fixed_windows=sum(c['windows']-c['valid'] for c in audio['chunks']),
    clipping=sum(c['clipping'] for c in audio['chunks']),residual_steps=len(audio['residual_steps']))
Path(f'coverage-{tag}.json').write_text(json.dumps(output,indent=2))
print({k:v for k,v in output.items() if k in ['profile_count','max_gap_at','overruns','over6099_ms','outside_max_ms','cymbals','unchecked_fixed_windows','clipping','residual_steps']})
print('missing',[(k,z['missing_blocks']) for k,z in streams.items()],'candidates',[(round(c['time_s'],4),c['verdict']) for c in checks])

