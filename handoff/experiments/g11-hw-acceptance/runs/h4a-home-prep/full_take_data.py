from pathlib import Path
import json,csv,sys
out=Path(__file__).resolve().parent
root=out.parents[1]
sys.path.insert(0,str(root))
from analyse_chase import read_blocks,np
lines=[]
for folder in sorted((root/'runs').glob('h4a-integration-*-01')):
    seg=json.loads((folder/'segments.json').read_text())
    loc=json.loads((folder/'locates.json').read_text())
    marks=json.loads((folder/'marker-phase.json').read_text())
    meta,pcm,b=read_blocks(folder/'driver')
    with (folder/'wire.csv').open() as f:
        q=[(int(row['qpc_ns']),int(row['hex'][2:],16)) for row in csv.DictReader(f) if row['hex'].startswith('f1')]
    for i,(r,m) in enumerate(zip(seg,marks,strict=True)):
        ref=r['first']-100_000_000
        cb=np.rint((b['qpc'].astype(float)*1e9/meta['qpc_frequency']-ref)/1000).astype('int64')
        cb=cb[(cb>=0)&(cb<=8_180_000)]
        lines += [f"{folder.name} {i} {folder.name.split('-')[2]} {m['first_frame']} {loc[2*i]['expected_sample']} {round(m['markers'][0]['t']*48000)}",
                  ' '.join(f'{round((t-ref)/1000)}:{v}' for t,v in q if r['first']<=t<=r['last']),
                  ' '.join(map(str,cb))]
assert len(lines)==300
(out/'full-take-timing.txt').write_text('\n'.join(lines))

