"""Read only the common prefix of the live witness files. Never touch their handles."""
import csv
import json
from datetime import datetime
from pathlib import Path

a = Path(__file__).resolve().parent
run = a / "combined-two-hours"

def read_complete_rows(path):
    raw = path.read_bytes()
    complete = raw[:raw.rfind(b"\n") + 1].decode("ascii").splitlines()
    return list(csv.DictReader(complete)), complete

source, lines = read_complete_rows(run / "source.csv")
incoming, _ = read_complete_rows(run / "ingress.csv")
source = [r for r in source if r["hex"].strip() == "f8"]
incoming = [r for r in incoming if r["hex"].strip() == "f8"]
n = min(len(source), len(incoming))
rows = []
for i in range(1, n):
    send = int(source[i]["send_ns"]) - int(source[i-1]["send_ns"])
    wire = int(incoming[i]["at_ns"]) - int(incoming[i-1]["at_ns"])
    if send > 50_000_000:
        rows.append(dict(next_pulse_zero_based=i, sender_interval_ms=send/1e6,
                         virtual_ingress_interval_ms=wire/1e6,
                         dispatch_late_ms=(int(source[i]["send_ns"])-int(source[i]["due_ns"]))/1e6,
                         index_multiple_of_256=i%256==0))
rows.sort(key=lambda row: row["sender_interval_ms"], reverse=True)
result = dict(as_of=datetime.now().astimezone().isoformat(), scope="in-progress common prefix, start-aligned by ordinal",
              complete_common_pulses=n, parsed_source=len(source), parsed_ingress=len(incoming),
              sender_intervals_over_50ms=len(rows), over_50ms_on_256_boundary=sum(r["index_multiple_of_256"] for r in rows),
              row_ascii_bytes_including_crlf=len(lines[1].encode("ascii"))+2,
              top=rows[:12])
(a/"source-spacing-diagnostic.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result,indent=2))
