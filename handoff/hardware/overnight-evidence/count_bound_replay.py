"""Evaluate an ordinal bound for continuous, zero-origin, zero-manual-offset passes only."""
import csv
import json
from pathlib import Path
import statistics
import sys

def times(path,kind):
    with path.open() as f:
        return [int(r["at_ns"]) for r in csv.DictReader(f) if r["hex"]==kind]

def replay(p):
    with (p/"result.json").open() as f:
        r=json.load(f)
    if r["dropout_count"] or [c["hex"] for c in r["controls"] if c["hex"] in ("fb","fa","fc")]!=["fa","fc"]:
        raise ValueError("Requires unbroken Start at zero, then Stop")
    incoming=times(p/"ingress.csv","f8")
    returned=times(p/"egress.csv","f8")
    if len(returned)<len(incoming):
        raise ValueError("For this comparison every input needs an output candidate")
    # Use wire observations as ideal eligibility times. No extra scheduling or port latency is simulated.
    delays=[max(0,s-e)/1e6 for e,s in zip(returned,incoming)]
    peak=delays.index(max(delays))
    bounded=[max(s,e) for e,s in zip(returned,incoming)]
    return dict(input=len(incoming), actual_output=len(returned), bounded_output=len(delays),
                withheld_at_end=len(returned)-len(delays),held=len([x for x in delays if x>0]),
                p95_added_ms=statistics.quantiles(delays,n=100,method="inclusive")[94],
                p99_added_ms=statistics.quantiles(delays,n=100,method="inclusive")[98],
                max_added_ms=max(delays), mean_added_ms=statistics.mean(delays),
                peak_input_seconds=(incoming[peak]-incoming[0])/1e9,
                observed_min_gap_ms=min(b-a for a,b in zip(returned,returned[1:]))/1e6,
                bounded_min_gap_ms=min(b-a for a,b in zip(bounded,bounded[1:]))/1e6)

if __name__=="__main__":
    folders=list(map(Path,sys.argv[1:]))
    rows={p.name:replay(p) for p in folders}
    print(json.dumps(rows,indent=2))
    (Path(__file__).resolve().parent/"stop-count-bound-replay.json").write_text(json.dumps(rows,indent=2))
