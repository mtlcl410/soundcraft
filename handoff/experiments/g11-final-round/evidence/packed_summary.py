"""Record every scored attack expressed in samples at 48 kHz, including empty/duplicate slots."""
from pathlib import Path
import csv, re, sys, ast
stem = sys.argv[1]
folder = Path(__file__).parent
log = (folder / f'{stem}.log').read_text(encoding='utf-8', errors='replace')
rows = []
summaries = []
for m in re.finditer(r'^HITS (\d+)-(\d+)-(\d+)-(VariableBurst|Burst\(\d+\)) (\[.*\])$', log, re.M):
    source, dest, cut = map(int, m.group(1,2,3))
    mode = m.group(4)
    slots = ast.literal_eval(m.group(5))
    n = cut + 193
    ideal = [0.]
    for j in range(1, n):
        ideal.append(ideal[-1]+2_500_000 / (source if j<=cut else dest))
    arrivals = [round(ideal[0])] if "phase4" in stem or "phase5" in stem or "final" in stem else []
    group = 0
    while len(arrivals)<n:
        p = len(arrivals)
        w = min(3+group%3 if mode=='VariableBurst' else int(mode[6:-1]), n-p)
        arrivals += [round(ideal[p+j]) if p==0 else round(ideal[p+w-1])+j*200 for j in range(w)]
        group += 1
    def nearest_sample(us):
        return int(us*0.048+0.5)
    for k, measured in enumerate(slots):
        ix=k*12
        wire=max(0, nearest_sample(arrivals[ix])-nearest_sample(ideal[ix]))
        for error in measured or [None]:
            rows.append(dict(source=source,dest=dest,cut=cut,mode=mode,eighth=k,post_cut=(ix>cut),ideal_sample=nearest_sample(ideal[ix]),arrival_sample=nearest_sample(arrivals[ix]),wire_samples=wire,actual_sample=None if error is None else nearest_sample(ideal[ix])+error,measured_samples=error,residual_samples=None if error is None else error-wire,slot_count=len(measured)))
    label=f'{source}-{dest}-{cut}-{mode}'
    case=re.search(rf'^CASE {re.escape(label)} missing=(\d+) extra=(\d+) damaged=(\d+) dropouts=(\d+).*',log,re.M)
    hits=[a for a in rows if a['source']==source and a['dest']==dest and a['mode']==mode and a['cut']==cut and a['post_cut'] and a['measured_samples'] is not None]
    summaries.append(dict(label=label,missing=int(case[1]),extra=int(case[2]),damaged=int(case[3]),dropouts=int(case[4]),max_wire_ms=max(a['wire_samples'] for a in hits)/48,worst_abs_residual_ms=max(abs(a['residual_samples']) for a in hits)/48,earliest_ms=min(a['measured_samples'] for a in hits)/48))
for name, table in [('eighths',rows), ('summary',summaries)]:
    if len(summaries) != 16:
        raise RuntimeError(f'Expected 16 cases, found {len(summaries)}')
    with (folder/f'{stem}-{name}.csv').open('w', newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f, fieldnames=table[0].keys());writer.writeheader();writer.writerows(table)
print(*summaries,sep='\n')
