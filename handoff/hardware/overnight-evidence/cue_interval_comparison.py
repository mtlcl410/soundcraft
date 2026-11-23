"""Summarize start, steady rolling and stop separately, using one receiving clock."""
from pathlib import Path
import csv
import json
import statistics
from stop_stage import analysis

here = Path(__file__).resolve().parent

def describe(values):
    if len(values) < 2:
        raise ValueError("insufficient events")
    q = statistics.quantiles(values, n=100, method="inclusive")
    return dict(n=len(values), minimum=min(values), p05=q[4], p50=statistics.median(values),
                p95=q[94], p99=q[98], maximum=max(values))

def read(path):
    with path.open() as stream:
        return [(int(row["at_ns"]), row["hex"]) for row in csv.DictReader(stream)]

def summarize(folder):
    before = read(folder / "ingress.csv")
    after = read(folder / "egress.csv")
    start, = (t for t, b in before if b == "fa")
    stop, = (t for t, b in before if b == "fc")
    streams = {}
    for name, pred, nominal in [("clock", lambda m: m == "f8", 60000 / (120 * 24)),
                                ("qf", lambda m: m.startswith("f1"), 1000 / 120)]:
        times = [t for t, b in after if pred(b) and t >= start]
        gaps = [(t, (t - prev) / 1e6) for prev, t in zip(times, times[1:])]
        rolling = [gap for t, gap in gaps if start + 1e9 <= t <= stop - 1e9]
        streams[name] = dict(technical_unit="ms", first_8_gaps=describe([v for _, v in gaps[:8]]),
                             steady_gaps=describe(rolling),
                             steady_absolute_error=describe([abs(v - nominal) for v in rolling]))
    return dict(streams=streams, stop=analysis(folder))

if __name__ == "__main__":
    captures = [f"cue-v{v}-{r}" for v in (1, 2) for r in range(1, 4)]
    out = {name: summarize(here / name) for name in captures}
    (here / "cue-comparison-six-trials.json").write_text(json.dumps(out, indent=2))
    for name, row in out.items():
        print(name, *[(k, round(v["first_8_gaps"]["minimum"], 3),round(v["steady_absolute_error"]["p95"], 3))
                      for k, v in row["streams"].items()])
