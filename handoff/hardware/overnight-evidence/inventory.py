"""Summarize completed evidence. Exclude correlation misses from all timing statistics."""
import csv,json,statistics,math
from pathlib import Path
a=Path(__file__).resolve().parent;d=a.parent;r=d/'runs/home-20261123-002520-recorder'
rows={}
for kind,rep,new,value,checksum in csv.reader((a/'bench.csv').open()):
    rows.setdefault(kind,{}).setdefault(new,[]).append((float(value),int(checksum)))
metrics={}
for kind,v in rows.items():
    assert len(v['false'])==len(v['true'])==9
    assert {c for data in v.values() for _,c in data}.__len__()==1
    metrics[kind]={s:round(statistics.median(x for x,_ in values),3) for s,values in v.items()}
m=json.loads((r/'marker-phase.json').read_text()); allrows=[]
for k,s in enumerate(m,1):
    for point in s['markers']:
        for side in ('rx','tx'):
            x=point[side]; allrows.append([k,point['t'],side,x['score'],x['ms'] if x['score']>.9 else None])
with (a/'recorder-all-markers.csv').open('w',newline='') as f:
    wr=csv.writer(f);wr.writerow(['roll','score_seconds','channel','correlation','error_ms_if_matched']);wr.writerows(allrows)
def profile(side,t):
    v=[row[4] for row in allrows if row[2]==side and row[4] is not None and abs(row[1]-(30 if row[0]==3 else 0)-t)<.001]
    return {'ms':v,'spread_ms':round(max(v)-min(v),4)} if v else {}
def summary_log(name):
    rows=[]
    for ln in (a/name).read_text(encoding='utf-8-sig',errors='replace').splitlines():
        if ln.startswith('PAIR,'):
            _,case,mode,onset,partial,counts=ln.split(',',5)
            rows.append([case,mode,int(onset),int(partial),json.loads(counts)])
    assert rows
    return {case:{'matched':sum(data[4]),'partial':data[3],'located_minus_rolling_us':data[2]-rolling[2]} for rolling,data in zip(rows[::2],rows[1::2]) for case in [data[0]]}
out={'bench_median_ns':metrics,'rx_first':profile('rx',.25),'tx_first':profile('tx',.25),'rx_after_preroll':profile('rx',2.25),'tx_after_preroll':profile('tx',2.25),'archived_replay':summary_log('recorded-wire-product.log'),'new_din_replay':summary_log('fresh-wire-product.log')}
(a/'results.json').write_text(json.dumps(out,indent=2))

