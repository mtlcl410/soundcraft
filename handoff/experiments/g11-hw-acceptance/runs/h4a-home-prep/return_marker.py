"""Secondary check for a known TX marker obscured by a lower-frequency return signal."""
from pathlib import Path
import json,sys
out=Path(__file__).resolve().parent
sys.path.insert(0,str(out.parents[1]))
from analyse_chase import read_blocks,source_samples,np

def verify(pcm,ix,lag,template,others):
    # Measure lag from an independent, clear marker of this take; search +-32 samples.
    # The second difference suppresses a slowly changing additive waveform.
    ref=np.diff(template.astype(float),n=2)
    lo=ix+lag-32
    wave=pcm[lo:ix+lag+32+len(template),1].astype(float)
    segments=np.lib.stride_tricks.sliding_window_view(np.diff(wave,n=2),len(ref))
    norms=np.linalg.norm(segments,axis=1)
    scores=(segments@ref)/np.maximum(norms*np.linalg.norm(ref),1.e-10)
    k=int(scores.argmax())
    choice=segments[k]
    gain=(choice@ref)/(ref@ref)
    other_scores=np.abs(others@choice)/np.maximum(np.linalg.norm(others,axis=1)*np.linalg.norm(choice),1e-10)
    return dict(score=float(scores[k]),gain=float(gain),lag=lag-32+k,other_max=float(other_scores.max()))
def audit(folder):
    meta,pcm,blocks=read_blocks(folder/'driver')
    source=source_samples()
    markers=json.loads((folder/'marker-phase.json').read_text())
    library=np.arange(12000,len(source)-127,24000)
    results=[]
    for take,rec in enumerate(markers):
        all_notes=rec['markers']
        correct=[m for m in all_notes if min(m['tx']['score'],m['rx']['score'])>=.85]
        if not correct:continue
        lags=[m['rx']['index']-m['tx']['index'] for m in correct]
        lag=int(np.median(lags))
        for m in all_notes:
            if m['tx']['score']<.85 or m['rx']['score']>=.85:continue
            j=m['tx']['index'];at=round(m['t']*meta['sample_rate'])
            templates=np.array([np.diff(source[i:i+127],n=2) for i in library if i!=at])
            v=verify(pcm,j,lag,pcm[j:j+127,0],templates)
            silent_control=verify(pcm,j+256,lag,pcm[j:j+127,0],templates)
            accepted=v['score']>=.98 and .90<=v['gain']<=1.10 and v['other_max']<.60 and silent_control['score']<.60
            results.append(dict(take=take+1,t=m['t'],original_rx=m['rx'],matched=v,shifted_control=silent_control,accepted=bool(accepted)))
    return results
if __name__=='__main__':
    root=out.parents[1]
    if len(sys.argv)>1:
        print(json.dumps(audit(Path(sys.argv[1])),indent=2))
    else:
        by_group={f.name:audit(f) for f in sorted((root/'runs').glob('h4a-integration-*-01'))}
        exceptions=[r for values in by_group.values() for r in values]
        assert len(exceptions)==1 and exceptions[0]['accepted'],exceptions
        print(exceptions)
        (out/'masked-return.json').write_text(json.dumps(by_group,indent=2))

