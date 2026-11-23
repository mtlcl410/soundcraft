import csv,re,collections,sys
from pathlib import Path
base=Path(__file__).parent
def rows(file):return list(csv.DictReader((base/file).open(encoding='utf-8-sig')))
def table(headers, data):
    return '\n'.join('| '+' | '.join(map(str,v))+' |' for v in [headers,['---']*len(headers),*data])
steady=rows('lead-data/device-lead-steady.csv')
sweep=rows('slowdown-summary.csv')
timing=[]
for i in range(18):
    h,p=sweep[i],sweep[i+18]
    def samples(row,key):return f"{int(row[key])/48:+.3f}"
    def st(policy):
        pair=[r for r in steady if all(r[x]==h[y] for x,y in [('bpm','bpm'),('buffer_samples','buffer'),('presentation_lead_ms','lead')]) and r['policy']==policy]
        return f"{min(float(r['min_ms']) for r in pair):+.3f}…{max(float(r['max_ms']) for r in pair):+.3f}"
    timing.append((h['bpm'],h['buffer'],h['lead'],st('Hard'),st('Predict'),samples(h,'off'),samples(p,'off'),samples(h,'beat'),samples(p,'beat')))
matrix=table(['BPM','Frames','Lead (ms)','Steady hard','Steady selected','Offbeat hard','Offbeat selected','Beat hard','Beat selected'],timing)
(base/'matrix.md').write_text(matrix,encoding='utf8')
if not (base/'packet-data/integrated-summary.csv').exists():sys.exit(0)
packet=rows('packet-data/integrated-summary.csv')
abrupt=[r for r in packet if not r['case'].startswith('A4')]
assert len(abrupt)==36
def get(r,*keys):
    return next((r[k] for k in keys if k in r),None)
def cell(r):return r['first_offbeat_ms']+' / '+r['from_second_beat_peak_ms']+' / '+r['first_confirm_delay_pulses']
group=collections.defaultdict(dict)
for r in abrupt:group[(r['from_bpm'],r['to_bpm'],r['transition'])][r['delivery']]=r
def delivery(r):return (0 if '1000' in r else 1 if '2000' in r else 2)
p_table=table(['Step (BPM)','Cut (F8)','±1 ms','±2 ms','3–5 packed'],[(k[0]+'→'+k[1],k[2],*[cell(v[t]) for t in sorted(v,key=delivery)]) for k,v in group.items()])
(base/'packet-matrix.md').write_text(p_table,encoding='utf8')
