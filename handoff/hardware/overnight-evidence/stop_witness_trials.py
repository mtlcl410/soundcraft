"""Pair the last successful midir handoff with the incoming Stop and the physical return."""
import json
import csv
import os
from pathlib import Path
import re
import sys
from cue_hardware import run

here = Path(__file__).resolve().parent
rows = []
rev = sys.argv[1]
ab = len(sys.argv)>2 and sys.argv[2]=='compensation'
for i, advance in enumerate((0, 0, 0, 0) if ab else (0, 15, 5, 0), 1):
    os.environ["SC_AUDIT_STOP_ADVANCE_MS"] = str(advance)
    label = f"stop-witness-{rev}-{i}"
    if ab:
        setting = ('on','off','off','on')[i-1]
        os.environ['SC_AUDIT_BEAT_COMPENSATION'] = setting
        label = f'compensation-{setting}-{i}'
    trial = run(label, f"{rev}-build.json", 12)
    folder = here / label
    matches = re.findall(r"SC_STOP_QPC (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)", (folder / "application.log").read_text(errors="replace"))
    with (folder / "egress.csv").open() as f:
        tail={r["hex"]:int(r["at_ns"]) for r in csv.DictReader(f) if r["hex"] in ("fc","f8")}
    # This test sends one FC. Do not align two processes using an uncalibrated epoch.
    sample, = (list(map(int,m)) for m in matches if int(m[0])>0)
    origin,host,audio,f8_begin,f8_end,fc_begin,fc_end=sample
    def delta(t):
        return (t-origin)/1e6
    with (folder / "ingress.csv").open() as f:
        seen,=(int(r["at_ns"]) for r in csv.DictReader(f) if r["hex"]=="fc")
    row=dict(label=label,advance_ms=advance,valid=trial['environment_valid'],count=trial['output_clock'],
             expected=trial['expected_clock'], return_f8_minus_input_fc_ms=(tail["f8"]-seen)/1e6,
             receipt_to_host_ms=delta(host) if host>=origin else None,
             receipt_to_callback_ms=delta(audio) if audio>=origin else None,
             receipt_to_f8_handoff_ms=delta(f8_begin),receipt_to_f8_handoff_end_ms=delta(f8_end),
             receipt_to_fc_handoff_ms=delta(fc_begin), return_fc_minus_input_fc_ms=(tail["fc"]-seen)/1e6)
    rows.append(row)
    name = "stop-compensation-abba.json" if ab else "stop-witness-comparison.json"
    (here/name).write_text(json.dumps(rows,indent=2))
    print(row,flush=True)
    if not row["valid"]:
        raise RuntimeError("Invalid environment")
