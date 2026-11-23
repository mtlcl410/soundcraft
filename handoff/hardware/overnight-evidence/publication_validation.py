"""Verify host polling separately once the physical run and cue trials release the host."""
import json
from pathlib import Path
import time
import traceback
from prearmed_validation import rust

folder = Path(__file__).resolve().parent
test = "clock_status_polls_publish_only_when_the_render_horizon_expires"

def status(phase, **fields):
    target = folder / "publication-progress.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(phase=phase, updated=time.strftime("%F %T"), **fields), indent=2))
    tmp.replace(target)

def main():
    status("waiting_for_device_tests_to_finish")
    for _ in range(5000):
        preceding = json.loads((folder / "prearmed-v3-progress.json").read_text())
        if preceding["stage"] in {"measured", "incomplete"}:
            hardware = json.loads((folder / "cue-v2-progress.json").read_text())
            if hardware["phase"] in {"measured", "incomplete"}:
                break
        time.sleep(2)
    else:
        raise TimeoutError("Earlier tests did not finish")
    status("checking_prior_version")
    tag = "poll-publication-red"
    red = rust(tag, "morning-publication-red", "g11-follow-target", [test, "--", "--nocapture"])
    log = (folder / f"prearmed-v3-{tag}.log").read_text(errors="replace")
    if not (red and "unchanged host polls republished the audio horizon" in log and f"{test} ... FAILED" in log):
        raise RuntimeError("Expected behavioural failure not confirmed")
    status("checking_fixed_suite")
    tag = "poll-publication-green"
    green = rust(tag, "morning-render-publication", "g11-verify-beat-target", ["--", "--test-threads=2"])
    log = (folder / f"prearmed-v3-{tag}.log").read_text(errors="replace")
    if green or f"{test} ... ok" not in log:
        raise RuntimeError("Expected suite and regression pass not confirmed")
    status("verified", old_unchanged_publications=1000, fixed_unchanged_publications=0,
           published_on_expiry=True, suite=next(line for line in log.splitlines() if line.startswith("test result:")))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        status("incomplete", error=traceback.format_exc())
        raise
