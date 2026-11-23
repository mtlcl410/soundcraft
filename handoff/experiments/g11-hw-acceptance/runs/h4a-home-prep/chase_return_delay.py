"""Separate same-stream sample lag from the callback timestamp used to label each endpoint."""
from pathlib import Path
import json,sys
from collections import Counter
here=Path(__file__).resolve().parent
root=here.parents[1]
def stats(folder):
    data=json.loads((folder/'marker-phase.json').read_text())
    result={}
    for mode in ['first','all']:
        ms=[m for r in data for m in (r['markers'][:1] if mode=='first' else r['markers']) if min(m['rx']['score'],m['tx']['score'])>=.85]
        samples=[m['rx']['index']-m['tx']['index'] for m in ms]
        if not samples:continue
        wall=[m['rx']['ms']-m['tx']['ms'] for m in ms]
        residual=[t-v/48 for v,t in zip(samples,wall)]
        result[mode]=dict(count=len(ms),sample_hist=dict(sorted(Counter(samples).items())),sample_span=max(samples)-min(samples),
                          wall_span_ms=round(max(wall)-min(wall),4),wall_minus_sample_extremes_ms=[round(min(residual),4),round(max(residual),4)])
    return result
if __name__=='__main__':
    groups=sorted((root/'runs').glob('h4a-integration-*-01'))+list(map(Path,sys.argv[1:]))
    data={x.name:stats(x) for x in groups}
    for name,r in data.items():print(name,r['first'],r['all']['sample_span'])
    (here/'chase-return-delay.json').write_text(json.dumps(data,indent=2))

