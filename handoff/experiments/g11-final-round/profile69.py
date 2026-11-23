"""Capture exact-revision library regressions, including the opt-in Clock profiles."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys

from analyze69 import analyze
from profile import profile

d = Path(__file__).resolve().parent
tree = d / "follow"
target = d.parent / "g11-verify-beat-target"


def commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tree, text=True).strip()


def check_tree(head):
    if commit() != head or subprocess.check_output(["git", "status", "--porcelain"], cwd=tree):
        raise SystemExit("Tree changed while measuring")


head = commit()
check_tree(head)
dest = d / "evidence" / f"1669-{head[:8]}"
dest.mkdir(exist_ok=True)
runner = str(d.parent / "g11-a10-recovery" / "run.cmd")
env = os.environ | {"CARGO_TARGET_DIR": str(target), "CARGO_TERM_COLOR": "never"}
bins = {}
for crate in ("soundcraft-playback", "soundcraft-ui-egui"):
    out = dest / ("profile-build-" + crate + ".log")
    with out.open("wb") as f:
        subprocess.run(["cmd", "/c", runner, "test", "--locked", "-p", crate, "--lib", "-j", "2", "--no-run"],
                       cwd=tree, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
    paths = re.findall(r"Executable unittests .*?\((.+?\.exe)\)", out.read_text(encoding="utf8"))
    [exe] = paths
    bins[crate] = Path(exe)
    check_tree(head)

filters = {
    "soundcraft-ui-egui": [
        ("dj_tempos::", False),
        ("twenty_full_length_dj_tracks", True),
        ("six_hour_clock_history_has_bounded_unreferenced_events", True),
        ("six_hour_clock_history_uncapped_control", True),
        ("eight_hours_of_clock_flutter", True),
        ("ten_minutes_of_coalesced", True),
        ("slowdown_device_phase_sweep", True),
        ("ramp_response::", False),
        ("packet_steps::", False),
        ("large_steps::", False),
        ("coast_relock::", False),
        ("brake::", False),
    ],
    "soundcraft-playback": [("locks_and_predicts_pulses_across_tempos_jitter_and_usb_quantization", False)],
}
rows = []
os.environ["SOUNDCRAFT_PACKET_TRACE"] = "1"
os.environ["SOUNDCRAFT_SWEEP_DIR"] = str(dest)
for crate, items in filters.items():
    for term, ignored in items:
        file = dest / ("profile-" + term.rstrip(":") + ".log")
        row = profile(bins[crate], term, file, ignored)
        check_tree(head)
        log = file.read_text(encoding="utf8", errors="replace")
        result = re.search(r"test result: [^\r\n]+", log)
        if not result or "0 passed; 0 failed;" in result.group():
            raise RuntimeError(f"No tests for {term}: {file}")
        row.update(head=head, name=term, ignored=ignored, result=result.group())
        rows.append(row)
        (dest / "profiles.json").write_text(json.dumps(rows, indent=2), encoding="utf8")
        if term in ["dj_tempos::", "twenty_full_length_dj_tracks"] and "signed eighth errors" in log:
            analyze(file, dest / term.strip(":"))
        print(term, row["code"], row["result"], flush=True)
sys.exit(int(any(row["code"] for row in rows)))
