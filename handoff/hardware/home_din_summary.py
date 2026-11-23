"""Compare only finished physical runs and report ONSET spread, absolute offsets and cadence."""
import csv,sys,json
from pathlib import Path
from statistics import median
from analyse_chase import np,read_blocks
root=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text('utf-8-sig'))
def midi(p,field):
    with p.open() as f:return [r[field] for r in csv.DictReader(f) if r[field].startswith(('f0','f1'))]

def inspect(path):
    r=read(path/'result.json')
    rows=read(path/'marker-phase.json')
    oldpath=root/'runs'/f"h4a-integration-{r['rate']}-{r['direction']}-01"
    old=read(oldpath/'marker-phase.json')
    meta,pcm,blocks=read_blocks(path/'driver')
    times=blocks['qpc']/meta['qpc_frequency']
    intervals=np.concatenate([np.diff(times[(times>=s['first']/1e9)&(times<=s['last']/1e9)])*1000 for s in read(path/'segments.json')])
    assert len(intervals)>0
    gaps=np.histogram(intervals,[0,2,4,7,10,50,200,240,260,np.inf])[0].tolist()
    tx,rx=midi(path/'tx.csv','hex'),midi(path/'wire.csv','hex')
    with (path/'tx.csv').open() as f:
        tags=[r['tag'] for r in csv.DictReader(f) if r['hex'].startswith(('f0','f1'))]
    if len(tx)==len(rx):
        mismatch=[dict(tag=k,sent=a,received=b) for k,a,b in zip(tags,tx,rx) if a!=b]
    else:
        mismatch=[dict(sent_count=len(tx),received_count=len(rx))]

    def stats(rows):
        z={}
        for ch in ('tx','rx'):
            first=[s['markers'][0][ch]['ms'] for s in rows if s['markers'] and s['markers'][0][ch]['score']>=.85]
            z[ch]=dict(count=len(first),median=round(median(first),4) if first else None,
                       spread=round(max(first)-min(first),4) if first else None)
        return z
    a,b=stats(old),stats(rows)
    valid=read(path/'environment-result.json')['environment_valid'] and meta['buffer']==256 and meta['sample_rate']==48000 and sum(gaps[6:])==0
    return dict(path=path.name,rate=r['rate'],direction=r['direction'],environment_valid=valid,
                passed=valid and tx==rx and bool(r['criteria_met']),prior=a,current=b,wire_equal=tx==rx,packet_differences=mismatch,
                hard_relocates=sum(z['diagnostic']['hard_relocates']-y['diagnostic']['hard_relocates'] for y,z in zip(*[iter(read(path/'locates.json'))]*2)),
                gap_bins=gaps,max_callback_ms=round(float(intervals.max()),4),mean_callback_ms=round(float(intervals.mean()),4))
if __name__=='__main__':
    batch=sys.argv[1]
    finished=[p for p in sorted((root/'runs').glob(f'home-{batch}-din-*')) if (p/'environment-result.json').exists() and (p/'result.json').exists()]
    output=[inspect(p) for p in finished]
    print(json.dumps(output,indent=2))

