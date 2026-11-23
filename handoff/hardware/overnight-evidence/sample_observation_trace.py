"""Use single past callback observations to predict an independently smoothed device position half a second later."""
from pathlib import Path
import json,struct,bisect,sys,csv
p=Path(sys.argv[1]);meta,=(p/'driver').glob('epoch-*.json');m=json.loads(meta.read_text());size=40+m['buffer']*8
freq=m['qpc_frequency'];n=meta.with_suffix('.bin').stat().st_size//size
with (p/'ingress.csv').open() as f:first=next(int(row['at_ns']) for row in csv.DictReader(f) if row['hex']=='f8')
with meta.with_suffix('.bin').open('rb') as f,(p/'projection-observations.tsv').open('w') as out:
    def at(i):
        f.seek(i*size);sample,_,qpc=struct.unpack('<QQQ',f.read(24))
        return qpc*1_000_000_000//freq,sample
    def find(t):
        return max(0,min(n-1,bisect.bisect_right(range(n),t,key=lambda i:at(i)[0])-1))
    def smoothed(t):
        i=find(t);a,x=at(max(0,i-24));b,y=at(min(n-1,i+24))
        return x+(t-a)*(y-x)/(b-a)
    zero=smoothed(first)
    for s in range(7199):
        t=first+s*1_000_000_000
        observed,sample=at(find(t))
        print(s,observed-first,sample-zero,smoothed(t+500_000_000)-zero,file=out)
