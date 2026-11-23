import csv
from pathlib import Path
from collections import Counter
from math import inf
base=Path(__file__).parent
def read(name):
    with (base/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def ms(n):return f'{int(n)/48:+.3f}'
def signed_worst(numbers):return max(numbers,key=abs,default=0)
for policy in ['hard','predict']:
    events=read(f'post-slow-{policy}.csv')
    parts={}
    # Detect the deadline for the physical output block containing the measured
    # onset. Its contents cannot be revised once committed. Only count samples
    # scheduled before the wire emits its first unexpectedly late pulse.
    for r in events:
        if r['actual_sample']=='' or r['stem']!='hat':continue
        bpm,buf,lead,cut,align,p,actual,off,beat,delta=[int(r[k]) for k in ('from_bpm','buffer','lead_ms','cut_pulse','callback_phase_samples','event_pulse','actual_sample','first_offbeat_pulse','first_beat_pulse','err_samples')]
        if p not in (off,beat):continue
        interval=120000//bpm
        first_cb=336*interval+align
        cb=first_cb+((actual-lead*48-first_cb)//buf)*buf
        horizon=cut*interval+interval # first missed old deadline
        key=(bpm,buf,lead)
        stats=parts.setdefault(key,dict(early=0,late=0,committed=0,retractable=0,min_error=0,max_error=0,committed_min=0))
        stats['min_error']=min(stats['min_error'],delta);stats['max_error']=max(stats['max_error'],delta)
        if delta<0:
            stats['early']+=1;stats['committed' if cb<horizon else 'retractable']+=1
            if cb<horizon:stats['committed_min']=min(stats['committed_min'],delta)
        elif delta>0:stats['late']+=1
    with (base/f'slowdown-{policy}-commit-window.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['bpm','buffer','lead_ms',*next(iter(parts.values()))])
        for k,v in parts.items():w.writerow([*k,*v.values()])
    print(policy,'earliest sample already in device output before first missing-pulse deadline:',min(s['committed_min'] for s in parts.values()))
