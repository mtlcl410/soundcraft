"""Identify every pulse across each entire rolling take using the original waveform library."""
from pathlib import Path
from collections import Counter
import json,sys
out=Path(__file__).resolve().parent
root=out.parents[1]
sys.path.insert(0,str(root))
from analyse_chase import np,read_blocks,source_samples
src=source_samples()
starts=np.flatnonzero(src)
positions=starts[np.r_[True,np.diff(starts)>3000]]
templates=np.array([src[i:i+127] for i in positions])
norms=np.linalg.norm(templates,axis=1)
unit=templates/norms[:,None]
rows=[]
folders = [Path(p) for p in sys.argv[1:]] or sorted((root/'runs').glob('h4a-integration-*-01'))
for folder in folders:
    marks=json.loads((folder/'marker-phase.json').read_text())
    segs=json.loads((folder/'segments.json').read_text())
    stops=json.loads((folder/'locates.json').read_text())
    info,pcm,blocks=read_blocks(folder/'driver')
    qpc=blocks['qpc']/info['qpc_frequency']
    n=info['buffer']
    for t,(rec,seg) in enumerate(zip(marks,segs,strict=True)):
        start=np.searchsorted(qpc,seg['first']/1e9-.02)
        finish=np.searchsorted(qpc,seg['last']/1e9+.4)
        gaps=np.diff(qpc[start:finish])*1000
        expected=[round(m['t']*48000) for m in rec['markers']]
        result={}
        ref_lag=rec['markers'][0]['rx']['index']-rec['markers'][0]['tx']['index']
        for channel in range(2):
            x=pcm[start*n:finish*n,channel]
            ix=np.flatnonzero(abs(x)>.00001)
            hits=ix[np.r_[True,np.diff(ix)>3000]] if len(ix) else []
            unknown = []
            if channel==0: tx_candidates=list(hits)
            if channel==1: hits=sorted(set(hits) | {i+ref_lag for i in tx_candidates})
            matched=[]
            for i in hits:
                observed=x[i:i+127]
                scores=np.abs(unit @ observed)/max(1e-12,np.linalg.norm(observed))
                top=int(scores.argmax())
                if scores[top] <= .85 or np.sum(scores>.85)!=1:
                    unknown.append([int(i),round(float(scores[top]),4)])
                    continue
                matched.append(int(positions[top]))
            counts=Counter(matched)
            result[str(channel)]={'missing':[k for k in expected if counts[k]==0],
                                  'extra':list((counts-Counter(expected)).elements()),'unidentified':unknown}
        before,after=stops[2*t:2*t+2]
        rows.append(dict(group=folder.name,take=t+1,first_expected=expected[0],expected=len(expected),channels=result,
                         hard_relocates=after['diagnostic']['hard_relocates']-before['diagnostic']['hard_relocates'],
                         gaps_ge_200=int((gaps>=200).sum()),max_gap_ms=round(float(gaps.max()),4)))
    g=rows[-10:]
    print(folder.name, sum(len(r['channels']['0']['missing']) for r in g),[r['hard_relocates'] for r in g],max(r['max_gap_ms'] for r in g))
assert len(rows)==10*len(folders)
for c in ['0','1']:
    print('channel',c,'expected',sum(r['expected'] for r in rows),'missing',sum(len(r['channels'][c]['missing']) for r in rows),'extra',sum(len(r['channels'][c]['extra']) for r in rows),'unidentified',sum(len(r['channels'][c]['unidentified']) for r in rows))
print('gap and relocation',max(r['max_gap_ms'] for r in rows),sum(r['gaps_ge_200'] for r in rows),sum(r['hard_relocates'] for r in rows))
(out/('all-markers-candidate.json' if sys.argv[1:] else 'all-markers.json')).write_text(json.dumps(rows,indent=2))

