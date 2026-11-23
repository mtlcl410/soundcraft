"""Three default-length starts, then four sources stopping at different offsets of their final tick."""
import csv
import json
import os
from pathlib import Path
from cue_hardware import run
from stop_stage import analysis

artifacts = Path(__file__).resolve().parent
rows = []
for i, (seconds, advance) in enumerate([(24, 0)]*3 + [(12, 15), (12, 0), (12, 10), (12, 5)], 1):
    os.environ['SC_AUDIT_STOP_ADVANCE_MS'] = str(advance)
    label = f'rounded-6849-{i}'
    row = run(label, '6849b48f-build.json', seconds)
    folder = artifacts / label
    with (folder/'ingress.csv').open() as stream:
        received = [(int(r['at_ns']), r['hex']) for r in csv.DictReader(stream)]
    last_pulse=max(t for t,m in received if m=='f8')
    stop, = (t for t,m in received if m=='fc')
    row.update(stop_advance_ms=advance, last_input_to_fc_ms=(stop-last_pulse)/1e6, stop=analysis(folder))
    rows.append(row)
    (artifacts/'rounded-phase-trials.json').write_text(json.dumps(rows,indent=2))
    print(label,advance,row['transport'],row['output_clock'],row['stop']['clock'],flush=True)
    if not row['environment_valid']:
        raise RuntimeError('Invalid environment; keep these records but do not combine results')
