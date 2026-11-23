"""Independently check the captured bytes from the staged G-11 physical output tests."""
from pathlib import Path
import json,statistics
root=Path(__file__).resolve().parent
rows=[(ts,p) for ts,n,p in map(json.loads,(root/'wire.jsonl').read_text().splitlines()) if n.startswith('UM-ONE')]
a,b=json.loads((root/'mtc-output-window.json').read_text())
mtc=[(ts,p) for ts,p in rows if a<=ts<=b]
q=[(ts,p[1]) for ts,p in mtc if p[0]==0xf1]
assert len(q)>200
assert all((a[1]//16+1)%8 == b[1]//16 for a,b in zip(q,q[1:]))
def frames(data):
    ff,ss,mm,hh=[(data[i]&15)|((data[i+1]&15)<<4) for i in range(0,8,2)]
    assert hh>>5==3 and ff<30 and ss<60 and mm<60
    return (((hh&31)*60+mm)*60+ss)*30+ff
groups=[frames([v for _,v in q[i:i+8]]) for i in range(len(q)-7) if q[i][1]>>4==0]
assert all(b==a+2 for a,b in zip(groups,groups[1:]))
assert [0xf0,127,127,1,1,96,0,2,0,247] in [p for _,p in mtc]
clock=[(ts,p) for ts,p in rows if ts<a and p[0] in (0xf8,0xfa,0xfb,0xfc,0xf2)]
groups_clocks=[]
for ts,p in clock:
    if p[0] in (0xfa,0xfb): groups_clocks.append([])
    if p[0]==0xf8: groups_clocks[-1].append(ts)
assert [p for ts,p in clock if p[0]!=248]==[[250],[252],[242,8,0],[251],[252]]
bpms=[60e9/24*(len(g)-1)/(g[-1]-g[0]) for g in groups_clocks]
assert all(abs(bpm-120)<2 for bpm in bpms)
s={'beat_clock_counts':[len(g) for g in groups_clocks],'beat_clock_bpm':bpms,'qf_count':len(q),'complete_qf_groups':len(groups),'qf_interval_median_ms':statistics.median((b[0]-a[0])/1e6 for a,b in zip(q,q[1:]))}
print(s)
(root/'output-results.json').write_text(json.dumps(s,indent=2))

