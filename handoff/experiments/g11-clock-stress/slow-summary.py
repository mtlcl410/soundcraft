import csv,collections,sys
from pathlib import Path
base=Path(__file__).parent
def worst(rows):
    return max((int(r['err_samples']) for r in rows if r['err_samples']),key=abs,default=0)
def dump(file, rows):
    with (base/file).open('w',newline='',encoding='utf8') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
allrows=[]; arrays={}
for label in ['hard','predict']:
    src=base/f'post-slow-{label}.csv'
    data=collections.defaultdict(list)
    for r in csv.DictReader(src.open()):data[tuple(int(r[k]) for k in ['from_bpm','buffer','lead_ms'])].append(r)
    arrays[label]=data
    for k,v in sorted(data.items()):
        song=[r for r in v if r['stem']=='hat']; clicks=[r for r in v if r['stem']=='click']
        cases=set((r['cut_pulse'],r['callback_phase_samples']) for r in v)
        assert len(cases)==96
        def e(stem,group):
            return worst(r for r in stem if r['event_pulse']==r['first_'+group+'_pulse'])
        clean=sum(r['waveform_ok']=='true' for r in v); no=sum(r['slot_count']=='0' for r in v);extra=sum(1-1/int(r['slot_count']) for r in v if int(r['slot_count'])>1)
        allrows.append(dict(policy=label,bpm=k[0],buffer=k[1],lead=k[2],cases=len(cases),off=e(song,'offbeat'),beat=e(song,'beat'),click=e(clicks,'beat'),unique_clean=clean,missing=no,duplicates=round(extra),bad=sum(r['actual_sample']!='' and r['waveform_ok']!='true' for r in v)))
for k,v in arrays['hard'].items():
    if k[1]/48000<60/(k[0]*24):assert v==arrays['predict'][k],k
dump('slowdown-summary.csv',allrows)
if __name__=='__main__':
    for name in ['hard','predict']:
        part=[r for r in allrows if r['policy']==name]
        print(name,*[max(part,key=lambda r:abs(r[f])) for f in ['off','beat']],sum(r['missing'] for r in part),sum(r['duplicates'] for r in part),sum(r['bad'] for r in part))
