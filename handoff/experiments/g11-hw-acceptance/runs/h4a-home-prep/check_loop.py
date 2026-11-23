"""Decompose output/return timing using archived PCM; no device I/O."""
from pathlib import Path
from collections import Counter
import json
import sys

out = Path(__file__).resolve().parent
root = out.parents[1]
sys.path.insert(0, str(root / 'audio'))
from m1 import read_blocks, measure, stimulus, np

samples, markers = stimulus()
groups = [f'm1-independent-{n}-{letter}' for n, letter in [(128,'a'),(256,'a'),(512,'c'),(512,'b')]]
groups += [f'm1-integration-{n}-formal-01' for n in (128,256,512)]
report = {}
for group in groups:
    path = root / 'runs' / group
    rows = []
    for take in sorted(path.glob('take-*')):
        meta, pcm, blocks = read_blocks(take)
        x = np.flatnonzero(abs(pcm[:,0]) > .00001)
        tx = x[np.r_[True,np.diff(x)>3000]]
        m = measure(take)
        assert m == json.loads((take/'summary.json').read_text())
        assert len(markers) == len(tx) == len(m['offsets'])
        rx = tx + m['offsets']
        tx_err = (tx-tx[0]) - (np.array(markers)-markers[0])
        rx_err = (rx-rx[0]) - (np.array(markers)-markers[0])
        rows.append(dict(take=take.name,tx=tx.tolist(),rx=rx.tolist(),tx_interval_error=tx_err.tolist(),
                         rx_interval_error=rx_err.tolist(),loop=m['offsets'],score=m['correlations'],reported=m['reported_samples']))
    assert len(rows)==20
    groupspread = max(max(r['loop']) for r in rows)-min(min(r['loop']) for r in rows)
    stable = sum(max(r['loop'])==min(r['loop']) for r in rows)
    tx_max = max(abs(v) for r in rows for v in r['tx_interval_error'])
    rx_max = max(abs(v) for r in rows for v in r['rx_interval_error'])
    valid=json.loads((path/'environment-result.json').read_text())['environment_valid']
    stats=dict(environment_valid=valid,spread=groupspread,all_six_constant=stable,max_tx_error=tx_max,max_rx_error=rx_max,
               peak_fit_min=min(min(r['score']) for r in rows),driver_totals=sorted({r['reported'] for r in rows}),
               first_marker_hist=dict(sorted(Counter(r['loop'][0] for r in rows).items())))
    report[group] = dict(stats=stats,takes=rows)
    print(group,valid,groupspread,stable,tx_max,rx_max)
    for r in rows:
        if len(set(r['loop']))>1: print(r['take'],r['loop'],r['tx_interval_error'],r['rx_interval_error'])
(out/'loop-decomposition.json').write_text(json.dumps(report,indent=2))

