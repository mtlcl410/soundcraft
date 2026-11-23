from pathlib import Path
from collections import Counter
d=Path(__file__).parent
for w in sorted(d.glob('wave-*.txt')):
 samples=[tuple(map(float,x.split())) for x in w.read_text().splitlines()];m=max(abs(a-b) for _,a,b in samples)
 print(w.stem,'max_abs',round(m,8),'different',sum(a!=b for _,a,b in samples),'n',len(samples),'first samples',samples[:3])
