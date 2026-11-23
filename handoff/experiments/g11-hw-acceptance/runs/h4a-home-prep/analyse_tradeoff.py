from collections import defaultdict
from pathlib import Path
from statistics import median
import json,re

out = Path(__file__).resolve().parent
log = (out/'pcm-tradeoff.log').read_text()
assert '2 passed; 0 failed' in log
tr = defaultdict(dict)
for us,pair,take,error in re.findall(r'PROBE,(\d+),([\w.\-]+),(\d+),(-?\d+),',log):
    tr[int(us)][(pair,int(take))] = int(error)
result = {}
for us, rows in sorted(tr.items()):
    assert len(rows)==100 and rows.keys()==tr[0].keys()
    ranges={p:max(v for (k,i),v in rows.items() if k==p)-min(v for (k,i),v in rows.items() if k==p) for p,_ in rows}
    gains=[tr[0][k]-v for k,v in rows.items()]
    result[us]=dict(worst_us=max(ranges.values()),pass_groups=sum(s<=3000 for s in ranges.values()),
                    ranges_us=ranges,median_gain_us=median(gains),min_gain_us=min(gains),max_gain_us=max(gains))
    print(us,result[us]['worst_us'],result[us]['pass_groups'],median(gains),min(gains),max(gains))
(out/'tradeoff-summary.json').write_text(json.dumps(result,indent=2))

