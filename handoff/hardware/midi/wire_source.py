"""Independent MTC/Clock stimulus, passive wire capture and private SoundCraft state sampling."""
import argparse
import contextlib
import csv
import json
import math
import queue
import sys
import threading
import time
from fractions import Fraction
from pathlib import Path

from midi_path import ARCHIVE, live_midi, prepare_run, write_json

NS = 1_000_000_000
RATES = {"24": (24, 1, 0), "25": (25, 1, 1), "29.97df": (30_000, 1001, 2),
         "29.97nd": (30_000, 1001, 3), "30": (30, 1, 3)}
STEPS = [(130, 80), (120, 100), (180, 60), (100, 120), (80, 130), (60, 180)]
CASES = ["steady120", "steady128", "nudge-up", "nudge-down", "brake1", "brake2", "half-double", "dj600",
         "soak7200", *[f"step-{a}-{b}" for a, b in STEPS]]


def tc(frame, rate):
    num, den, code = RATES[rate]
    nominal = round(num / den)
    frame %= 2_589_408 if code == 2 else 86400 * nominal
    if code == 2:
        tens, part = divmod(frame, 17_982)
        frame += tens * 18 + 2 * max(0, (part - 2) // 1798)
    seconds, frames = divmod(frame, nominal)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return (code << 5) | hours, minutes, seconds, frames


def full(frame, rate):
    return (0xf0, 0x7f, 0x7f, 1, 1, *tc(frame, rate), 0xf7)


def mtc(rate, takes):
    num, den, _ = RATES[rate]
    interval = Fraction(NS * den, num * 4)
    roll_frames = 2 * round(num / den * 4)
    end = 0
    for take in range(takes):
        # An even frame starts each two-frame, eight-piece sequence. Alternate zero and nonzero locates.
        origin = 0 if take % 2 == 0 else 2 * round(num / den)
        yield end, full(origin, rate), f"take-{take + 1}:locate-frame-{origin}"
        start = end + NS
        for i in range(roll_frames * 4):
            piece = i % 8
            h, m, s, f = tc(origin + 2 * (i // 8), rate)
            field = (f, s, m, h)[piece // 2]
            data = (piece << 4) | ((field >> (4 * (piece % 2))) & 15)
            yield start + round(i * interval), (0xf1, data), f"take-{take + 1}:qf-{i}"
        end = start + round(roll_frames * 4 * interval)
        yield end, full(origin + roll_frames, rate), f"take-{take + 1}:stopped-frame-{origin + roll_frames}"
        end += NS


def bpm_for(case, pulse):
    if case.startswith("step-"):
        _, a, b = case.split("-")
        return float(a if pulse < 192 else b)
    if case.startswith("brake"):
        width = 24 if case == "brake1" else 48
        return 128 - 123 * min(1., max(0., (pulse - 192) / width))
    if case == "half-double":
        return 87 if 192 <= pulse < 384 else 174
    if case.startswith("nudge-"):
        return 128 * (1 + ((.05 if case == "nudge-up" else -.05) if 192 <= pulse < 240 else 0))
    if case == "dj600":
        tempos = [118, 126, 132, 120, 129, 124]
        span = 16 * 96
        section, phase = divmod(pulse, span)
        return tempos[section % len(tempos)] + (tempos[(section + 1) % len(tempos)] - tempos[section % len(tempos)]) * phase / span
    return 128 if case == "steady128" else 120


def clock(case):
    end_s = {"dj600": 600, "soak7200": 7200, "steady120": 600}.get(case)
    count = 192 + (24 if case == "brake1" else 48) + 48 if case.startswith("brake") else 576
    yield 0, (0xfa,), "start"
    steady = case in ("steady120", "soak7200")
    if steady:
        count = end_s * 48
    at = 0.
    pulse = 0
    while (at < end_s if case == "dj600" else pulse < count):
        bpm = bpm_for(case, pulse)
        yield round(at * NS), (0xf8,), f"p{pulse}@{bpm:.8f}"
        pulse += 1
        at = pulse / 48 if steady else at + 2.5 / bpm
    yield round((end_s if end_s is not None else at) * NS), (0xfc,), "stop"


def sleep_until(deadline):
    while True:
        remaining = deadline - time.perf_counter_ns()
        if remaining <= 0:
            return
        # Short waits release the GIL; do not busy-spin on the host running SoundCraft.
        time.sleep(remaining / NS)


def source(directory, port, events):
    with live_midi(tx_name=port) as (tx, _, names), (directory / "tx.csv").open("x", newline="") as f:
        write_json(directory / "ports.json", names)
        rows = csv.writer(f)
        rows.writerow(["event_index", "tag", "bytes_hex", "scheduled_qpc_ns", "send_entry_qpc_ns", "send_return_qpc_ns"])
        origin = time.perf_counter_ns() + 200_000_000
        clock_running = False
        try:
            for i, (delta, msg, tag) in enumerate(events):
                due = origin + delta
                sleep_until(due)
                sent = time.perf_counter_ns()
                tx.send_message(list(msg))
                returned = time.perf_counter_ns()
                clock_running = False if msg == (0xfc,) else clock_running or msg == (0xfa,)
                rows.writerow([i, tag, bytes(msg).hex(), due, sent, returned])
        finally:
            if clock_running:
                tx.send_message([0xfc])


def capture(directory, port, seconds):
    with live_midi(rx_name=port) as (_, inbox, names), (directory / "rx.csv").open("x", newline="") as f:
        write_json(directory / "ports.json", names)
        rows = csv.writer(f)
        rows.writerow(["sequence", "rx_callback_qpc_ns", "bytes_hex", "backend_delta_s"])
        end = time.perf_counter_ns() + round(seconds * NS)
        index = 0
        while (remaining := (end - time.perf_counter_ns()) / NS) > 0:
            try:
                stamp, packet, delta = inbox.get(timeout=min(.25, remaining))
            except queue.Empty:
                continue
            rows.writerow([index, stamp, bytes(packet).hex(), delta])
            index += 1
        # Include callbacks timestamped inside the window even if Python did not poll immediately.
        while not inbox.empty():
            stamp, packet, delta = inbox.get_nowait()
            if stamp <= end:
                rows.writerow([index, stamp, bytes(packet).hex(), delta])
                index += 1
        write_json(directory / "window.json", {"stop_qpc_ns": end, "received": index, "seconds": seconds})


def poll(directory, control_port, seconds, step):
    sys.path.insert(0, str(ARCHIVE))
    from desktop_sync import cmd
    with (directory / "status.jsonl").open("x", encoding="utf-8") as f:
        end = time.perf_counter_ns() + round(seconds * NS)
        while time.perf_counter_ns() < end:
            for method in ("setup.midi_sync_status", "transport.status"):
                before = time.perf_counter_ns()
                value = cmd(control_port, method)
                print(json.dumps({"before_qpc_ns": before, "after_qpc_ns": time.perf_counter_ns(),
                                  "method": method, "value": value}), file=f, flush=True)
            time.sleep(step)


def selftest():
    assert tc(1800, "29.97df") == (64, 1, 0, 2) and tc(17_982, "29.97df") == (64, 10, 0, 0)
    for rate in RATES:
        events = list(mtc(rate, 2))
        assert events[0][1] == full(0, rate)
        assert [msg[1] >> 4 for _, msg, _ in events[1:9]] == list(range(8))
        assert all(a[0] <= b[0] for a, b in zip(events, events[1:]))
        assert sum(msg[0] == 0xf0 for _, msg, _ in events) == 4
    for case in CASES:
        prev = -1
        count = 0
        for at, msg, tag in clock(case):
            assert at >= prev
            if msg == (0xf8,):
                assert tag.startswith(f"p{count}@")
                count += 1
            prev = at
        assert count > 0 and msg == (0xfc,)
        if case == "soak7200":
            assert count == 345600
    print("PASS: all MIDI stimulus cases at virtual time; no port opened.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["plan", "selftest", "clock", "mtc", "capture", "poll"])
    p.add_argument("--case", choices=CASES, default="steady120")
    p.add_argument("--rate", choices=RATES, default="30")
    p.add_argument("--takes", type=int, default=10)
    p.add_argument("--seconds", type=float, default=20)
    p.add_argument("--poll-interval", type=float, default=.05)
    p.add_argument("--port", default="UM-ONE")
    p.add_argument("--control-port", type=int)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    if a.mode == "selftest":
        return selftest()
    if a.mode == "plan":
        return print(json.dumps({"clock_cases": CASES, "chase_rates": list(RATES), "clock_direction": "tool TX (SoundCraft RX)",
                                 "capture_direction": "tool RX (SoundCraft TX)", "mtc_stop": "cease QFs, send stopped full-frame locate"}))
    if a.out is None or not 1 <= a.takes <= 100 or not 0 < a.seconds <= 10800 or not .01 <= a.poll_interval <= 60:
        p.error("supply a new --out directory, 1–100 takes, positive duration ≤10800 s, and poll interval 0.01–60 s")
    if a.mode == "poll" and not a.control_port:
        p.error("poll needs an isolated desktop --control-port")
    directory = prepare_run(a.out)
    if a.mode == "capture":
        capture(directory, a.port, a.seconds)
    elif a.mode == "poll":
        poll(directory, a.control_port, a.seconds, a.poll_interval)
    else:
        source(directory, a.port, clock(a.case) if a.mode == "clock" else mtc(a.rate, a.takes))


if __name__ == "__main__":
    main()

