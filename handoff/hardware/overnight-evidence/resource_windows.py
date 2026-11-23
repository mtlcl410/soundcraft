import json
from pathlib import Path
from statistics import median
import sys

def report(folder):
    data=[json.loads(x) for x in (folder/'state.jsonl').read_text().splitlines()]
    active=[r for r in data if r['s']['clock_follow']['state']=='Locked']
    begin=active[0]['at_ns'];period=600*10**9
    wins=[]
    for k in range(12):
        rows=[r for r in active if begin+k*period<=r['at_ns']<begin+(k+1)*period]
        if not rows:continue
        out=rows[-1]['s']['output'];mem=[r['private_bytes'] for r in rows]
        wins.append(dict(window=k+1,count=len(rows),median_private_bytes=median(mem),
                    range_private_bytes=[min(mem),max(mem)],max_observer_queue=max(r['drain_q'] for r in rows),
                    output_lateness_max_us_cumulative=out['lateness_max_us'],late_callbacks_cumulative=out['callback_gaps_over_two_buffers'],
                    backlog_drops_cumulative=out['session_backlog_drops']))
    return wins
if __name__=='__main__':
    p=Path(sys.argv[1]);v=report(p);(p/'resource-windows.json').write_text(json.dumps(v,indent=2))
    for r in v:print(r['window'],r['median_private_bytes'],r['max_observer_queue'],r['late_callbacks_cumulative'])
