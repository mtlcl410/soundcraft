"""Place counterexamples on the source, relay, returning MIDI and ASIO time axes."""
import bisect
import csv
import json
from pathlib import Path
import sys

folder=Path(sys.argv[1])

def read(name, key, value, kind):
    with (folder/name).open() as stream:
        return [int(row[key]) for row in csv.DictReader(stream) if row["hex"].startswith(value) and
                (kind is None or int(row["hex"][-2:],16)//16==kind)]

start,=read("ingress.csv","at_ns","fa",None)
series = {
    "source_f8":read("source.csv","send_ns","f8",None),
    "physical_in_f8":read("relay.csv","arrival_ns","f8",None),
    "virtual_in_f8":read("ingress.csv","at_ns","f8",None),
    "physical_return_f8":read("egress.csv","at_ns","f8",None),
    "physical_return_qf":read("egress.csv","at_ns","f1",None),
}
with (folder/"decoded-mtc-vs-device.json").open() as f:
    cases=json.load(f)["groups_beyond_5ms"]
for case in cases:
    center=start+round(case["seconds_after_start"]*1e9)
    case["max_adjacent_gaps_ms"]={}
    for key, times in series.items():
        left=bisect.bisect_left(times,center-150_000_000)
        right=bisect.bisect_right(times,center+150_000_000)
        case["max_adjacent_gaps_ms"][key]=max((t-s)/1e6 for s,t in zip(times[left:right-1],times[left+1:right]))
(folder/"mtc-outlier-stages.json").write_text(json.dumps(cases,indent=2))
print(max(cases,key=lambda x:abs(x["res_ms"])) if cases else "no outliers")
