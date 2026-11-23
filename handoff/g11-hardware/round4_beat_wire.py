"""Windows G-11 clock-output acceptance. Without --run only the test plan is printed."""
import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import socket
import statistics
import subprocess
import sys
import time

from desktop_sync import cmd, rpc

ROOT = Path(__file__).resolve().parent
F8, START, CONTINUE, STOP, SPP = 0xF8, 0xFA, 0xFB, 0xFC, 0xF2


def plan(case):
    if case == "r3":
        # 20 BPM gives a 125 ms wire period, without phase ambiguity for the
        # approximately 47 ms device lead measured on this WASAPI path.
        return [dict(bpm=20, compensate=enabled, multiplier=scale)
                for enabled in (True, False) for scale in (0.5, 2)]
    if case == "phase":
        return [dict(bpm=bpm, origin=0, offsets=[0, -200, 0]) for bpm in (120, 180)]
    if case in ("r1", "r1-min"):
        return [dict(trial=i + 1, bpm=120, origin=0, offset=0) for i in range(5 if case=="r1-min" else 20)]
    if case == "r5":
        # On this 10 ms device the RPC, the next callback and the external round
        # trip together can exceed one buffer. Use 1–3 clock pulses of margin.
        return [dict(trial=i + 1, bpm=120, origin=0, offset=0, before_end_ms=[60, 48, 40, 34, 28][i % 5]) for i in range(20)]
    return [dict(bpm=bpm, origin=origin, offset=offset) for bpm in (120, 180) for origin in (0, 47_125) for offset in (0, -200)]


def assess(case, trial, packets, requested, stop_requested, position, before, after, stop_acknowledged=None):
    """Retain raw packets and independently check their order at the receiving port."""
    controls = [(t, msg) for t, msg in packets if msg[0] in (START, CONTINUE, STOP, SPP)]
    clocks = [t for t, msg in packets if msg[0] == F8]
    tags = [msg[0] for _, msg in controls]
    first = next(((t, msg[0]) for t, msg in packets if msg[0] in (START, CONTINUE)), None)
    checks = {"clock_observed": len(clocks) >= 3, "first_clock_after_launch": bool(first and clocks and clocks[0] >= first[0]),
              "last_clock_before_stop": bool(controls and controls[-1][1] == [STOP] and clocks and clocks[-1] <= controls[-1][0]),
              "starts_within_second": bool(first and 0 <= first[0] - requested <= 10**9),
              "sent_increased": after.get("sent", 0) > before.get("sent", 0),
              "transition_timeouts_unchanged": after["pending_transition_timeouts"] == before["pending_transition_timeouts"]}
    if case in ("r1", "r1-min"):
        checks["no_transition_timeouts"] = after["pending_transition_timeouts"] == 0
    if trial["origin"]:
        expected = math.ceil(trial["origin"] / (48_000 * 60 / trial["bpm"] / 4))
        checks["wire_transport"] = tags == [SPP, CONTINUE, STOP] and controls[0][1] == [SPP, expected & 127, expected >> 7]
    else:
        checks["wire_transport"] = tags == [START, STOP]
    if len(clocks) >= 3:
        wire_bpm = 60e9 * (len(clocks)-1) / (24 * (clocks[-1] - clocks[0])) if clocks[-1] > clocks[0] else None
        if case == "grid":
            checks["wire_bpm"] = wire_bpm is not None and abs(wire_bpm - trial["bpm"]) < 2
    else:
        wire_bpm = None
    first_wrap = None
    if case == "r5" and tags.count(START) + tags.count(CONTINUE) > 1:
        first_wrap = next((t for t, msg in controls if msg == [STOP]), None)
    if case == "r5":
        checks["stopped_near_loop_end"] = isinstance(position, (int, float)) and 90_000 <= position <= 96_512
        checks["receiver_near_first_bar_end"] = 91 <= len(clocks) <= 97
    samples_per_sixteenth = 48_000 * 60 / trial["bpm"] / 4
    expected_delay_ms = (math.ceil(trial["origin"] / samples_per_sixteenth) * samples_per_sixteenth - trial["origin"]) / 48
    measured_delay_ms = (clocks[0] - first[0]) / 1e6 if clocks and first else None
    if case == "grid":
        # Launch commands are emitted before the first sixteenth boundary. Both observations
        # share the same receiving clock. Allow at most one 24-PPQN clock of arrival variation.
        checks["first_clock_within_one_pulse_of_grid"] = measured_delay_ms is not None and abs(measured_delay_ms - expected_delay_ms) < 60_000 / (24 * trial["bpm"])
    classification = "pass" if all(checks.values()) else "failed"
    if first_wrap is not None and first_wrap < stop_requested:
        classification = "already_wrapped_before_stop_request"
    elif first_wrap is not None and stop_acknowledged is not None and first_wrap <= stop_acknowledged:
        classification = "wrapped_while_stop_rpc_in_flight"
    return {"checks": checks, "pass": classification == "pass",
            "classification": classification,
            "clocks": len(clocks), "control_bytes": controls, "expected_first_grid_delay_ms": expected_delay_ms,
            "wire_bpm": wire_bpm, "first_clock_delay_ms": (clocks[0] - first[0]) / 1e6 if clocks and first else None,
            "first_clock_from_play_call_ms": (clocks[0] - requested) / 1e6 if clocks else None,
            "stop_requested_ns": stop_requested, "stopped_sample": position}


def phase_shift(bpm, segments):
    """Phase at the receiver on one uninterrupted grid. Interpolate between both zero-offset observations."""
    period = 60e9 / (24 * bpm)
    anchor = segments[0][0]

    def wrap(value):
        return (value + period / 2) % period - period / 2

    centers, phases, spreads = [], [], []
    for clocks in segments:
        centers.append(statistics.mean(clocks))
        angles = [(t-anchor) * 2 * math.pi / period for t in clocks]
        direction = math.atan2(sum(map(math.sin, angles)), sum(map(math.cos, angles))) * period / (2 * math.pi)
        residuals = [wrap(t-anchor-direction) for t in clocks]
        phases.append(direction + statistics.median(residuals))
        p10, *_, p90 = statistics.quantiles(residuals, n=10, method="inclusive")
        spreads.append((p90-p10) / 1e6)
    weight = (centers[1] - centers[0]) / (centers[2] - centers[0])
    reference = phases[0] + weight * wrap(phases[2] - phases[0])
    return {"receiver_advance_ms": wrap(phases[1] - reference)/1e6,
            "zero_to_zero_drift_ms": wrap(phases[2] - phases[0])/1e6, "phase_p90_minus_p10_ms": spreads,
            "clocks_used": [len(s) for s in segments]}


def measure_phase(port, capture, raw, args, compensation, data):
    for trial in plan("phase"):
        cmd(port, "event.tempo", at=0, bpm=trial["bpm"])
        observations, clocks = [], []
        for i, offset in enumerate(trial["offsets"]):
            cmd(port, "setup.midi_beat_clock", enabled=True, destination=args.midi_out, offset=offset, compensation=compensation)
            if i == 0:
                cmd(port, "transport.play", **{"from": 0})
            start = time.perf_counter_ns()
            time.sleep(2.25)
            stop = time.perf_counter_ns()
            stamps = []
            while True:
                try:
                    t, msg = capture.get_nowait()
                except queue.Empty:
                    break
                raw.write(json.dumps([f"phase-{trial['bpm']}-{i}", t, msg]) + "\n")
                if start+500_000_000 <= t <= stop and msg == [F8]:
                    stamps.append(t)
            clocks.append(stamps)
            output = cmd(port, "setup.midi_sync_status")["output"]
            transport = cmd(port, "transport.status")
            observations.append({"offset": offset, "window_ns": [start+500_000_000, stop], "output": output, "transport": transport})
        cmd(port, "transport.stop")
        seen = all(len(group) >= 12 for group in clocks) and all(obs["transport"]["playing"] for obs in observations)
        result = {"spec": trial, "observations": observations, "pass": False}
        if seen:
            measured = phase_shift(trial["bpm"], clocks)
            diagnostics = [obs["output"]["ports"][args.midi_out] for obs in observations]
            middle = diagnostics[1]
            zero_at_same_lead_us = middle["device_lead_us"] + middle["system_delay_samples"] * 1e6 / 48_000
            expected = (middle["effective_total_us"] - zero_at_same_lead_us)/1000
            result.update(measured, requested_change_ms=-200/48, diagnostics_change_ms=expected,
                          receiver_minus_diagnostics_ms=measured["receiver_advance_ms"]-expected)
            result["pass"] = True  # Acquisition only; report the observed effect and jitter, without a fabricated tolerance.
        data["trials"].append(result)
        print("continuous phase", trial["bpm"], {k:v for k,v in result.items() if k not in ("observations","spec")}, flush=True)

def measure_r3(port, capture, raw, args, compensation, data):
    for spec in plan("r3"):
        cmd(port, "event.tempo", at=0, bpm=spec["bpm"])
        settings = dict(compensation, beat_clock=spec["compensate"])
        setup = dict(enabled=True, destination=args.midi_out, compensation=settings)
        cmd(port, "setup.midi_beat_clock", offset=0, **setup)
        cmd(port, "transport.play", **{"from": 0})
        time.sleep(.65)
        initial = cmd(port, "setup.midi_sync_status")["output"]["ports"][args.midi_out]
        if initial["device_lead_us"] <= 0:
            raise RuntimeError("no measured device lead")
        wanted = -round(initial["device_lead_us"] * .048 * spec["multiplier"])
        clocks, diagnostics = [], []
        for i, offset in enumerate((0, wanted, 0)):
            acknowledged = cmd(port, "setup.midi_beat_clock", offset=offset, **setup)
            start = time.perf_counter_ns()
            time.sleep(3.5)
            end = time.perf_counter_ns()
            stamps = []
            while True:
                try:
                    t, msg = capture.get_nowait()
                except queue.Empty:
                    break
                raw.write(json.dumps([["r3", spec, i], t, msg]) + "\n")
                if start+500_000_000 <= t <= end and msg == [F8]:
                    stamps.append(t)
            clocks.append(stamps)
            diagnostics.append(cmd(port, "setup.midi_sync_status")["output"]["ports"][args.midi_out])
        cmd(port, "transport.stop")
        t = diagnostics[1]
        available = (t["device_lead_us"] + t["system_delay_samples"] / .048) if spec["compensate"] else 0
        requested = available + t["offset_samples"] / .048
        floor = min(available, 1000)
        expected_total = max(requested, floor)
        phase = phase_shift(spec["bpm"], clocks) if all(len(row)>=12 for row in clocks) else {}
        checks = dict(continuous_phase_observed=bool(phase), advance_limited=t["advance_limited"] == (requested < floor),
                      effective_total_us=abs(expected_total-t["effective_total_us"]) <= 2, offset_applied=t["offset_samples"] == wanted)
        expected_change = (expected_total-available)/1000
        result = dict(spec=spec, initial=initial, requested_samples=wanted, snapshots=diagnostics, checks=checks,
                      expected_change_ms=expected_change, pass_result=all(checks.values()), **phase)
        result["pass"] = result.pop("pass_result")
        if phase:
            result["wire_minus_predicted_ms"] = phase["receiver_advance_ms"] - expected_change
        data["trials"].append(result)
        print("r3", spec, checks, phase, flush=True)


@contextlib.contextmanager
def desktop(executable, directory):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = directory / "private-settings"
    config.mkdir()
    env = dict(os.environ, SOUNDCRAFT_CONFIG_DIR=str(config), SOUNDCRAFT_NO_PREFS="1")
    with (directory / "desktop.log").open("xb") as log:
        process = subprocess.Popen([str(executable), "--control", str(port)], env=env, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(180):
                if process.poll() is not None:
                    raise RuntimeError("dedicated SoundCraft instance exited during startup")
                try:
                    cmd(port, "transport.status")
                    break
                except (OSError, ValueError):
                    time.sleep(.25)
            else:
                raise TimeoutError("private desktop control socket did not become ready")
            yield port, process.pid
        finally:
            if process.poll() is None:
                for method, args in (("transport.stop", {}), ("setup.midi_beat_clock", {"enabled": False})):
                    with contextlib.suppress(OSError, ValueError):
                        cmd(port, method, **args)
                time.sleep(.2)
                process.terminate()
                process.wait(timeout=15)


def run(case, args):
    sys.path.insert(0, str(ROOT / "capture-deps"))
    import rtmidi
    directory = args.evidence / (case + "-" + str(time.time_ns()))
    directory.mkdir(parents=True, exist_ok=False)
    with args.exe.open("rb") as binary:
        digest = hashlib.file_digest(binary, "sha256").hexdigest()
    data = {"case": case, "commit_as_supplied": args.commit, "exe": str(args.exe.resolve()), "exe_sha256": digest, "trials": []}
    queue_in = queue.SimpleQueue()
    input_port = rtmidi.MidiIn()
    names = input_port.get_ports()
    matches = [i for i, name in enumerate(names) if args.midi_in in (name, re.sub(r" [0-9]+$", "", name))]
    data["available_midi_inputs"] = names
    try:
        if len(matches) != 1:
            raise RuntimeError(f"Expected one {args.midi_in!r} input; available {names!r}. Evidence {directory}")
        input_port.ignore_types(sysex=False, timing=False, active_sense=True)
        input_port.set_callback(lambda event, _: queue_in.put((time.perf_counter_ns(), list(event[0]))))
        input_port.open_port(matches[0])
        with desktop(args.exe.resolve(), directory) as (port, pid), (directory/"wire.jsonl").open("x", encoding="utf-8", buffering=1) as raw:
            data["ports"] = {"input": names[matches[0]], "output": args.midi_out}
            cmd(port, "session.new", name="G-11 dedicated clock wire acceptance", sample_rate=48000)
            systems = cmd(port, "ui.audio_device", list=True)["systems"]
            candidates = [d for h in systems if h["is_default"] for d in h["outputs"]
                          if "model 12" in d["name"].lower() and (not args.audio_device or args.audio_device == d["name"])]
            data["model_12_outputs"] = candidates
            if len(candidates) != 1:
                raise RuntimeError(f"Choose the exact --audio-device from default-host outputs: {systems!r}")
            device = candidates[0]
            max_buffer = min(8192, device.get("buffer_max") or 8192)
            buffer = args.buffer or (max_buffer if case in ("r1","r1-min") else 256)
            cmd(port, "ui.audio_device", output=device["name"], buffer_size=buffer, sample_rate=48000)
            audio = cmd(port, "setup.playback_engine")
            data["playback_engine"] = audio
            if not audio.get("applied") or "model 12" not in str(audio.get("device")).lower() or audio.get("sample_rate") != 48000:
                raise RuntimeError(f"Expected an active 48 kHz Model 12 output. Actual {audio!r}")
            if audio.get("buffer_size") != buffer:
                raise RuntimeError(f"Requested {buffer}, device reported {audio.get('buffer_size')}. Supply a verified --buffer value.")
            if case == "r5":
                data["requested_spec_buffer"] = 256
                data["exact_spec_buffer"] = audio["buffer_size"] == 256
                if not data["exact_spec_buffer"] and not args.buffer:
                    raise ValueError("R5 calls for 256 frames. For supplementary evidence supply the verified actual --buffer.")
            config = cmd(port, "setup.midi_beat_clock")
            compensation = dict(config["compensation"], beat_clock=case != "r5")
            cmd(port, "options.loop_playback", value=case == "r5")
            if case == "r5":
                cmd(port, "options.insertion_follows_playback", value=False)
            if case == "r1-min":
                from round4_mtc_wire import minimized_window
                user, handle = minimized_window(pid)
                user.ShowWindow(handle, 6)
                time.sleep(.25)
                if not user.IsIconic(handle):
                    raise RuntimeError("The dedicated SoundCraft window did not minimize")
                data["shortcut"] = "ui.key Space on the private minimized app"
            if case == "r3":
                measure_r3(port, queue_in, raw, args, compensation, data)
                return all(t["pass"] for t in data["trials"])
            if case == "phase":
                measure_phase(port, queue_in, raw, args, compensation, data)
                return all(t["pass"] for t in data["trials"])
            for i, trial in enumerate(plan(case)):
                cmd(port, "event.tempo", at=0, bpm=trial["bpm"])
                if case == "r5":
                    cmd(port, "edit.select", start=0, end=96_000)
                elif case == "r1-min":
                    cmd(port, "transport.locate", at=0)
                cmd(port, "setup.midi_beat_clock", enabled=True, destination=args.midi_out, offset=trial["offset"], compensation=compensation)
                time.sleep(5 if case in ("r1","r1-min") else .35)
                before = cmd(port, "setup.midi_sync_status")["output"]
                if case == "grid":
                    # A separately tested reconnect aligns an already rolling slave
                    # by SPP/Continue. This case starts from an established route.
                    cutoff = time.monotonic() + 4
                    while not before["ports"].get(args.midi_out, {}).get("connected"):
                        if time.monotonic() >= cutoff:
                            raise TimeoutError("Beat Clock output did not open before the grid transport test")
                        time.sleep(.025)
                        before = cmd(port, "setup.midi_sync_status")["output"]
                requested = time.perf_counter_ns()
                if case == "r1-min":
                    if not user.IsIconic(handle):
                        raise RuntimeError("The dedicated SoundCraft window left its minimized state")
                    rpc(port, "ui.key", {"key": "Space"})
                else:
                    cmd(port, "transport.play", **({} if case == "r5" else {"from": trial["origin"]}))
                play_acknowledged = time.perf_counter_ns()
                packets = []

                def drain():
                    while True:
                        try:
                            t, msg = queue_in.get_nowait()
                        except queue.Empty:
                            break
                        raw.write(json.dumps([i, t, msg]) + "\n")
                        if t >= requested and msg:
                            packets.append((t, msg))

                if case == "r5":
                    deadline = time.monotonic() + 1.5
                    while time.monotonic() < deadline:
                        drain()
                        start = next((t for t, m in packets if m == [START]), None)
                        if start is not None:
                            target = start + 2_000_000_000 - trial["before_end_ms"] * 1_000_000
                            time.sleep(max(0, (target-time.perf_counter_ns())/1e9))
                            break
                        time.sleep(.001)
                else:
                    time.sleep(2.5 if case == "grid" else 1.1)
                stop_requested = time.perf_counter_ns()
                if case == "r1-min":
                    rpc(port, "ui.key", {"key": "Space"})
                else:
                    cmd(port, "transport.stop")
                stop_acknowledged = time.perf_counter_ns()
                time.sleep(.3)
                drain()
                status = cmd(port, "transport.status")
                after = cmd(port, "setup.midi_sync_status")["output"]
                result = assess(case, trial, packets, requested, stop_requested, status.get("position"), before, after, stop_acknowledged)
                data["trials"].append({"spec": trial, "requested_ns": requested, "play_acknowledged_ns": play_acknowledged,
                                       "stop_acknowledged_ns": stop_acknowledged, "before": before, "after": after, "transport": status, **result})
                print(case, i+1, result["pass"], result["checks"], flush=True)
            if case == "grid":
                comparisons = []
                for zero, advance in zip(data["trials"][::2], data["trials"][1::2]):
                    a, b = zero["first_clock_from_play_call_ms"], advance["first_clock_from_play_call_ms"]
                    comparisons.append({"bpm": zero["spec"]["bpm"], "origin": zero["spec"]["origin"],
                                        "requested_change_ms": -200 / 48, "observed_call_to_clock_change_ms": b-a if a is not None and b is not None else None})
                data["offset_comparisons"] = comparisons
                data["offset_reference"] = "The play-call timestamp includes UI, device-buffer and USB scheduling. Exact audio-relative advance requires a common audio/MIDI reference."
    except Exception as problem:
        data["error"] = str(problem)
        raise
    finally:
        if input_port.is_port_open():
            input_port.close_port()
        (directory/"summary.json").write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        print(directory, flush=True)
    return len(data["trials"]) == len(plan(case)) and all(trial["pass"] for trial in data["trials"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("r1","r1-min","r5","grid","phase","r3"), required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--commit")
    parser.add_argument("--midi-in", default="UM-ONE")
    parser.add_argument("--midi-out", default="Model 12 MIDI")
    parser.add_argument("--audio-device")
    parser.add_argument("--buffer", type=int)
    parser.add_argument("--evidence", type=Path, default=ROOT/"round4-wire")
    args = parser.parse_args()
    if not args.run:
        print(json.dumps(plan(args.case), indent=2))
    elif not args.exe or not args.commit or not re.fullmatch(r"[0-9a-fA-F]{40}", args.commit):
        parser.error("--run requires an executable and its exact 40-character source commit")
    else:
        sys.exit(0 if run(args.case, args) else 1)
