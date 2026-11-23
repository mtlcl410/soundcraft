"""Use the hardware only after the preceding two-hour acquisition has released it."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import traceback

from cue_hardware import run as measure
from stop_stage import analysis

artifacts = Path(__file__).resolve().parent
acceptance = artifacts.parent
test = "a_prearmed_zero_start_one_pulse_late_does_not_jump_to_the_next_sixteenth"

def progress(stage, **extra):
    target = artifacts / "prearmed-v3-progress.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(stage=stage, local_time=time.strftime("%Y-%m-%d %H:%M:%S %z"), **extra), indent=2))
    tmp.replace(target)

def logged(tag, cmd, cwd, env=None):
    with (artifacts / f"prearmed-v3-{tag}.log").open("xb") as log:
        return subprocess.run(cmd, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800).returncode

def rust(tag, tree, target, args):
    wrapper = acceptance.parent / "g11-a10-recovery/run.cmd"
    cmd = [os.environ["COMSPEC"], "/d", "/c", str(wrapper), "test", "--offline", "-p", "soundcraft-playback", "--lib", *args]
    return logged(tag, cmd, acceptance / tree, os.environ | {"CARGO_TARGET_DIR": str(acceptance.parent / target)})

def main():
    progress("waiting_for_exclusive_device")
    for _ in range(3900):
        latest = json.loads((artifacts / "cue-v2-progress.json").read_text())
        if latest["phase"] == "measured":
            break
        if latest["phase"] == "incomplete":
            if not (artifacts / "cue-v2-two-hours/environment-result.json").exists():
                raise RuntimeError("The preceding acquisition did not confirm hardware release")
            break
        time.sleep(2)
    else:
        raise TimeoutError("Preceding physical measurement still active")
    progress("red_before_fix")
    rc = rust("red", "morning-prearmed-red", "g11-follow-target", [test, "--", "--nocapture"])
    log = (artifacts / "prearmed-v3-red.log").read_text(errors="replace")
    if not (rc and f"{test} ... FAILED" in log and "assertion" in log):
        raise RuntimeError("Expected a behavioural test failure; inspect red.log")
    progress("fixed_playback_suite")
    if rust("green", "morning-cue-prearmed", "g11-verify-beat-target", ["--", "--test-threads=2"]):
        raise RuntimeError("Fixed playback tests failed")
    log = (artifacts / "prearmed-v3-green.log").read_text(errors="replace")
    if f"{test} ... ok" not in log:
        raise RuntimeError("New regression was missing from the green suite")
    progress("building_hardware_candidate")
    tree = acceptance / "morning-v3-hardware"
    rev = subprocess.check_output(["git", "-C", tree, "rev-parse", "--short=8", "HEAD"], text=True).strip()
    if logged("build", [sys.executable, str(acceptance / "audio/build_tools.py"), "soundcraft", "--tree", str(tree)], acceptance):
        raise RuntimeError("Physical test build failed")
    rows = []
    for i in range(1, 4):
        progress("measuring_physical_starts", trial=i, completed=len(rows))
        label = f"prearmed-v3-{i}"
        row = measure(label, f"{rev}-build.json", 24)
        row["stop"] = analysis(artifacts / label)
        rows.append(row)
        (artifacts / "prearmed-v3-summary.json").write_text(json.dumps(rows, indent=2))
        if not row["environment_valid"]:
            raise RuntimeError("Physical trial environment invalid")
    lines = ["# 已在歌頭待命時的 Clock 起播複測", "", "Model 12、UM-ONE，48 kHz／256。每輪 24 秒。", "",
             "| 輪次 | 起播 | 首 F8（ms） | 首八個間距最小（ms） | F8 實收／預期 | QF 實收／預期 |",
             "|---:|---|---:|---:|---:|---:|"]
    starts = 0
    for i, row in enumerate(rows, 1):
        commands = row["transport"]
        start = "Start" if "fa" in commands and "fb" not in commands else "Continue" if "fb" in commands else "未辨識"
        starts += start == "Start"
        edge = row["detail"]
        lines.append(f"| {i} | {start} | {edge['first_clock_after_input_start_ms']:.3f} | {min(edge['first_8_clock_intervals_ms']):.3f} | {row['output_clock']}／{row['expected_clock']} | {row['qf']}／{row['expected_qf']} |")
    lines += ["", f"三輪中有 {starts} 輪從零送 Start。Clock 與 QF 總數各自判定。[三輪完整數據](prearmed-v3-summary.json)"]
    (artifacts / "prearmed-v3-result.zh-TW.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    progress("measured", zero_starts=starts, physical_trials=len(rows))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        progress("incomplete", error=traceback.format_exc())
        raise
