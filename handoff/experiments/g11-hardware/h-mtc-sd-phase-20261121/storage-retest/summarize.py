"""Summarize audible timing and the output latency observations around A4."""
from pathlib import Path
import json
import os
import statistics
import sys

root = Path(os.environ.get("SOUNDCRAFT_STORAGE_TAKE_DIR", Path(__file__).resolve().parent)).resolve()
baseline = 11.619
for name in sys.argv[1:]:
    result = json.loads((root / name / "result.json").read_text())
    rows = [json.loads(line) for line in (root / (name + "-samples.jsonl")).read_text().splitlines()]
    near = [r["diagnostic"] for r in rows if "diagnostic" in r and 3 < r["qpc"] - result["anchor_qpc"] < 6]
    assert near
    values = [r["reported_lead_us"] for r in near if r["reported_lead_us"] is not None]
    render = result["render_delay_ms"]
    print(json.dumps(dict(take=name, delay_ms=render,
          delta_ms=None if render is None else round(render - baseline, 3),
          measured=(render is not None), within_band=None if render is None else abs(render-baseline) <= 3,
          match=result["correlation"], qf=result["qf_count"],
          source=sorted({r["lead_source"] for r in near}),
          lead_ms=None if not values else round(statistics.median(values)/1000, 3),
          rejected=near[-1]["lead_clamps"]-near[0]["lead_clamps"])))
