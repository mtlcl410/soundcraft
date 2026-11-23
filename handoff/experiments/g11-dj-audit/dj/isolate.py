from pathlib import Path
from array import array
import csv,sys
p=Path(__file__).parent/'differential'
assert sys.byteorder=='little'
def load(file):
 a=array('f');a.frombytes(file.read_bytes());return a
with (p/'velocity-isolation.csv').open('w',newline='') as h:
 w=csv.writer(h);w.writerow(['case','note_id','on_sample','off_sample','span_samples','abs_delta_peak'])
 for x in sorted(p.glob('*~*.f32')):
    name,idx=x.stem.split('~'); orig=load(p/f'{name}.f32');variant=load(x)
    assert len(orig)==len(variant)
    groups=[]
    for i,(a,b) in enumerate(zip(orig,variant)):
        if a==b:continue
        if not groups or i-groups[-1][-1][0]>7:groups.append([])
        groups[-1].append((i,abs(a-b)))
    if not groups:w.writerow([name,idx,'','','',0])
    for g in groups:w.writerow([name,idx,g[0][0],g[-1][0]+1,g[-1][0]-g[0][0]+1,max(z[1] for z in g)])
print((p/'velocity-isolation.csv').read_text())
