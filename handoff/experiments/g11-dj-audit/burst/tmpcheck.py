import csv
from pathlib import Path
d=Path(__file__).parent
with (d/'eighths.csv').open() as f: a=list(csv.DictReader(f))
for a0,b in [('180','60'),('130','80')]:
  rows=[x for x in a if x['from_bpm']==a0 and x['packet_timing']=='TrailingBurst' and x['transition_pulse']=='384' and x['counterexample']=='false']
  target=[round((i*30/int(a0) if i<=32 else 32*30/int(a0)+(i-32)*30/int(b))*48000) for i in range(49)]
  print(a0,b)
  for i,e in enumerate(target):
    if i<31:continue
    r=[(int(row['pcm_onset_sample'])-e,int(row['voice_samples'])) for row in rows if min(range(len(target)),key=lambda j:abs(target[j]-int(row['pcm_onset_sample'])))==i]; print(i,r,end='; ')
  print()
