"""Inventory only by default. Optional sampling reads an existing SoundCraft desktop control port."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from desktop_sync import cmd

root = Path(__file__).resolve().parent
trees = {1662: "g11-beat-clock", 1663: "g11-mtc", 1669: "g11-clock-follow"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, help="control port of an already-running test instance")
    parser.add_argument("--seconds", default=0.0, type=float)
    parser.add_argument("--interval", default=0.1, type=float)
    parser.add_argument("--case", default="inventory")
    parser.add_argument("--output", type=Path, required=True, help="new JSON evidence file")
    args = parser.parse_args()
    if args.seconds < 0 or args.interval <= 0 or (args.seconds and not args.port):
        parser.error("a timed sample requires a control port, nonnegative duration and positive interval")
    probe = root.parent / "tascam-model-12" / "hui" / "model12_midi_probe.py"
    # Without arguments this utility calls only GetNumDevs / GetDevCaps.
    ports = json.loads(subprocess.check_output([sys.executable, "-X", "utf8", str(probe)], text=True, encoding="utf-8"))
    commits = {}
    for pr, directory in trees.items():
        checkout = root.parent / directory
        commits[pr] = subprocess.check_output(
            ["git", "-c", "safe.directory=" + checkout.as_posix(), "-C", str(checkout), "rev-parse", "HEAD"], text=True
        ).strip()
    result = {"case": args.case, "utc": datetime.now(timezone.utc).isoformat(), "checkout_heads": commits,
              "winmm_ports": ports, "control_port": args.port, "samples": []}
    with args.output.open("x", encoding="utf-8") as out:
        if args.port:
            start = time.monotonic()
            while True:
                sample = {"elapsed_s": time.monotonic() - start}
                try:
                    for method in ("setup.midi_sync_status", "transport.status"):
                        sample[method] = cmd(args.port, method)
                except (OSError, ValueError) as err:
                    sample["error"] = str(err)
                sample["elapsed_end_s"] = time.monotonic() - start
                result["samples"].append(sample)
                if sample["elapsed_end_s"] >= args.seconds:
                    break
                time.sleep(min(args.interval, args.seconds - sample["elapsed_end_s"]))
        json.dump(result, out, ensure_ascii=False, indent=2)
        out.write("\n")


if __name__ == "__main__":
    main()
