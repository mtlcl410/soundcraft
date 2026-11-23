"""Export auditable onset-by-onset results printed by the production PCM fixture."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
from pathlib import Path


def analyze(log: Path, dest: Path):
    dest.mkdir(exist_ok=True, parents=True)
    cases = []
    with (dest / "dj-eighths.csv").open("w", encoding="utf8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case", "eighth", "signed_samples_at_48k", "signed_ms"])
        for line in log.read_text(encoding="utf8", errors="replace").splitlines():
            if "signed eighth errors (48 kHz samples)" not in line:
                continue
            label, raw = line.split(" signed eighth errors (48 kHz samples) ", 1)
            label = re.sub(r"^test \S+ \.\.\. ", "", label)
            notes = ast.literal_eval(raw)
            for i, s in enumerate(notes):
                writer.writerow([label, i, s, format(s / 48, "+.6f")])
            cases.append(dict(case=label, eighths=len(notes), early=min(notes) / 48, late=max(notes) / 48))
    if not cases:
        raise ValueError("Missing rendered note series")
    table = dest / "dj-eighths.csv"
    stats = dict(cases=len(cases), eighths=sum(r["eighths"] for r in cases),
                 sha256=hashlib.sha256(table.read_bytes()).hexdigest(),
                 cases_with_complete_waveforms=cases)
    (dest / "dj-case-summary.json").write_text(json.dumps(stats, indent=2), encoding="utf8")
    print(table, stats["cases"], stats["eighths"], stats["sha256"])


if __name__ == "__main__":
    analyze(Path(sys.argv[1]), Path(sys.argv[2]))
