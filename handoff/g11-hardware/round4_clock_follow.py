"""Read clock-follow diagnostics and record separate optional WinMM taps. No outbound MIDI."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import re
import statistics
import sys
import time

from desktop_sync import cmd

MESSAGES = {0xf2: "SPP", 0xf8: "Clock", 0xfa: "Start", 0xfb: "Continue", 0xfc: "Stop"}


def summarize(rows):
    per_source = {}
    states = []
    host_runs = []
    active_run = None
    for r in rows:
        if "raw" in r:
            source = per_source.setdefault(r["tap"], {"counts": {}, "transport": [], "ticks": []})
            kind = MESSAGES[r["raw"][0]]
            source["counts"][kind] = source["counts"].get(kind, 0) + 1
            if kind == "Clock":
                source["ticks"].append(r["at_ns"])
            else:
                record = {"at_ns": r["at_ns"], "message": kind}
                if kind == "SPP" and len(r["raw"]) == 3:
                    record["sixteenths"] = r["raw"][1] + 128 * r["raw"][2]
                source["transport"].append(record)
        if "follow" in r:
            state = r["follow"].get("state")
            playing = r["transport"].get("playing")
            bpm = r["follow"].get("estimated_bpm")
            if playing:
                if active_run is None:
                    active_run = {"start_ns": r["at_ns"], "first_position":r["transport"].get("position"), "locked_bpm": []}
                active_run["last_position"] = r["transport"].get("position")
                if state == "Locked" and isinstance(bpm,(float,int)):
                    active_run["locked_bpm"].append(bpm)
            elif active_run is not None:
                active_run["stopped_ns"] = r["at_ns"]
                host_runs.append(active_run)
                active_run = None
            if not states or (states[-1]["state"], states[-1]["playing"]) != (state, playing):
                states.append({"at_ns":r["at_ns"], "state":state, "playing":playing, "bpm":r["follow"].get("estimated_bpm"),
                               "position":r["transport"].get("position")})
    for source in per_source.values():
        clocks = source.pop("ticks")
        for action in source["transport"]:
            if action["message"] not in ("Start", "Continue"):
                continue
            until = next((a["at_ns"] for a in source["transport"] if a["message"] == "Stop" and a["at_ns"] > action["at_ns"]), 2**63)
            pulse = [t for t in clocks if action["at_ns"] <= t < until]
            if len(pulse) >= 25:
                periods = [(pulse[i] - pulse[i-24]) / 1e9 for i in range(24,len(pulse)) if pulse[i] > pulse[i-24]]
                if periods:
                    action["bpm_median"] = round(60/statistics.median(periods), 2)
            action["clocks"] = len(pulse)
    if active_run:
        host_runs.append(active_run)
    for run in host_runs:
        estimates = run.pop("locked_bpm")
        if estimates:
            run["host_bpm_median"] = round(statistics.median(estimates), 3)
            run["host_bpm_last"] = round(estimates[-1], 3)
    return {"observed_wire":per_source, "observed_host_transitions":states, "observed_host_runs":host_runs}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--port", type=int, help="control port of an already configured SoundCraft instance")
    ap.add_argument("--tap", action="append", default=[], help="exact input name, e.g. UM-ONE or Model 12 MIDI; may be supplied more than once")
    ap.add_argument("--seconds", type=float, default=180)
    ap.add_argument("--stop-file", type=Path)
    args = ap.parse_args()
    if args.seconds <= 0 or not (args.port or args.tap):
        ap.error("choose a positive duration and a data source")
    q = queue.SimpleQueue()
    with args.output.open("x", encoding="utf8", buffering=1) as file, ExitStack() as stack:
        def log(o):
            file.write(json.dumps(o, ensure_ascii=False) + "\n")
        log({"utc":datetime.now(timezone.utc).isoformat(), "clock":"perf_counter_ns", "source":"104a9fc", "control_port":args.port})
        if args.port:
            baseline = cmd(args.port, "setup.midi_sync_status")
            log({"at_ns":time.perf_counter_ns(), "initial":baseline})
            f = baseline["clock_follow"]
            if not f.get("enabled"):
                raise ValueError("Enable Clock Follow and the designated input before collecting evidence")
        if args.tap:
            sys.path.insert(0, str(Path(__file__).parent/"capture-deps"))
            import rtmidi
            for name in args.tap:
                incoming = rtmidi.MidiIn()
                matches = [i for i, n in enumerate(incoming.get_ports()) if n == name or re.sub(r" [0-9]+$", "", n) == name]
                if len(matches) != 1:
                    log({"tap":name, "unavailable":"missing or ambiguous"})
                    continue
                try:
                    incoming.ignore_types(sysex=True, timing=False, active_sense=True)
                    incoming.set_callback(lambda e, _, n=name: q.put((time.perf_counter_ns(), n, e[0])) if e[0] and e[0][0] in MESSAGES else None)
                    incoming.open_port(matches[0])
                except Exception as err:
                    log({"tap":name, "unavailable":str(err)})
                    continue
                stack.callback(incoming.close_port)
                log({"tap":name,"opened":True})
        print("READY", flush=True)
        end = time.monotonic() + args.seconds
        next_poll = 0
        def drain():
            while not q.empty():
                stamp, name, data = q.get_nowait()
                log({"at_ns":stamp,"tap":name,"raw":list(data)})
        while time.monotonic() < end and not (args.stop_file and args.stop_file.exists()):
            drain()
            if args.port and time.monotonic() >= next_poll:
                stamp = time.perf_counter_ns()
                try:
                    follow = cmd(args.port, "setup.midi_clock_follow")
                    transport = cmd(args.port, "transport.status")
                    log({"at_ns":stamp,"reply_ns":time.perf_counter_ns(),"follow":follow,"transport":transport})
                except (OSError, ValueError) as err:
                    log({"at_ns":stamp,"control_error":str(err)})
                next_poll = time.monotonic()+0.09
            time.sleep(0.01)
        drain()
        if args.port:
            log({"at_ns":time.perf_counter_ns(), "final":cmd(args.port, "setup.midi_sync_status")})
    with args.output.open(encoding="utf8") as inp:
        print(json.dumps(summarize(map(json.loads, inp)),ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
