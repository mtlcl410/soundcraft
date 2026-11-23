from pathlib import Path
import csv,sys,collections
D=Path(__file__).parent
rows=list(csv.DictReader((D/'eighths.csv').open()))
summary=list(csv.DictReader((D/'summary.csv').open()))
fail=False
for x in summary:
    if x['counterexample']!='false': continue
    k=tuple(x[s] for s in ['from_bpm','to_bpm','transition_pulse','packet_timing','counterexample'])
    vals=collections.defaultdict(list)
    for r in rows:
        if tuple(r[s] for s in ['from_bpm','to_bpm','transition_pulse','packet_timing','counterexample'])!=k: continue
        if r['delta_ms']: vals[int(r['eighth_index'])].append(float(r['delta_ms']))
    c=int(x['transition_pulse'])//12
    issues=[]
    for i in range(c+1,c+17):
        if len(vals[i])!=1: issues.append(f'eighth {i}: {len(vals[i])} attacks')
        tol=10 if i==c+1 else 4
        for v in vals[i]:
            if abs(v)>tol: issues.append(f'eighth {i}: {v:+.6f}ms (threshold {tol}ms)')
    if int(x['malformed']): issues.append(x['malformed']+' malformed waveforms')
    if int(x['dropouts']): issues.append(x['dropouts']+' observed dropouts')
    if issues: fail=True
    print('FAIL' if issues else 'PASS',k,' | '.join(issues))
sys.exit(int(fail))
