import csv,json
from pathlib import Path
from collections import Counter
here=Path(__file__).resolve().parent
runs=here.parent
def changes(points):
    return [dict(previous=a[0],next=b[0],before=a[1],after=b[1],delta=b[1]-a[1]) for a,b in zip(points,points[1:]) if a[1]!=b[1]]
matrix={}
for folder in sorted(runs.glob('h4a-integration-*-01')):
    items=json.loads((folder/'marker-phase.json').read_text())
    points=[((i+1,r['t']),r['rx']['index']-r['tx']['index']) for i,s in enumerate(items) for r in s['markers'] if min(r['tx']['score'],r['rx']['score'])>=.85]
    matrix[folder.name]=changes(points)
with (runs/'m3-sd-01/sd-drift-pairs.csv').open() as f:
    raw=[{k:int(row[k]) for k in ('code_index','asio_output','asio_input9','sd')} for row in csv.DictReader(f)]
sdout=changes([(r['code_index'],r['sd']-r['asio_output']) for r in raw])
usbin=changes([(r['code_index'],r['asio_input9']-r['asio_output']) for r in raw])
print(Counter(t['delta'] for a in matrix.values() for t in a))
print(sum(bool(a) for a in matrix.values()),'of',len(matrix),'groups changed')
print('SD-output changes',sdout,'USB input-output changes',usbin)
(here/'long-return-steps.json').write_text(json.dumps(dict(matrix=matrix,sd_output=sdout,usb_input_output=usbin),indent=2))

