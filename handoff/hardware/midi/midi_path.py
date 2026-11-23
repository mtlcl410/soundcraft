"""Independent Windows MIDI ruler. A plan or offline self-test never enumerates devices."""
import argparse
import contextlib
import csv
import json
import math
import os
import queue
import re
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent.parent / "g11-hardware"
COUNT = 10_000
PERIOD_NS = 20_833_333
QUIET_NS = 250_000_000
F8 = (0xF8,)


def write_json(path, data):
    with path.open("x", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)


def endpoint(names, requested):
    matches = [(i, name) for i, name in enumerate(names) if re.sub(r" \d+$", "", name) == requested or name == requested]
    if len(matches) != 1:
        raise ValueError(f"Expected one {requested!r} endpoint, found {matches!r}. Available: {names!r}")
    return matches[0]


@contextlib.contextmanager
def live_midi(tx_name=None, rx_name=None):
    # Use exactly the Windows MM path and the python-rtmidi build used in round4_follow_loop.py.
    sys.path.insert(0, str(ARCHIVE / "capture-deps"))
    import rtmidi

    inbox = queue.SimpleQueue()
    with contextlib.ExitStack() as stack:
        ports = {}
        if rx_name:
            rx = rtmidi.MidiIn(rtapi=rtmidi.API_WINDOWS_MM)
            idx, ports["receive"] = endpoint(rx.get_ports(), rx_name)
            def receive(event, _):
                stamp = time.perf_counter_ns()
                message, driver_delta = event
                inbox.put((stamp, tuple(message), driver_delta))
            rx.ignore_types(sysex=False, timing=False, active_sense=False)
            rx.set_callback(receive)
            stack.callback(rx.cancel_callback)
            rx.open_port(idx)
            stack.callback(rx.close_port)
        tx = None
        if tx_name:
            tx = rtmidi.MidiOut(rtapi=rtmidi.API_WINDOWS_MM)
            idx, ports["send"] = endpoint(tx.get_ports(), tx_name)
            tx.open_port(idx)
            stack.callback(tx.close_port)
        yield tx, inbox, ports


def check_quiet(inbox, seconds, observe):
    deadline = time.perf_counter() + seconds
    while True:
        try:
            msg = inbox.get(timeout=max(0, deadline-time.perf_counter()))
        except queue.Empty:
            return
        observe(*msg)
        if msg[1] != (0xFE,):
            raise ValueError(f"Unsolicited message outside an F8 request: {msg!r}")


def get_f8(inbox, observe):
    deadline = time.perf_counter() + 1
    while time.perf_counter() < deadline:
        msg = inbox.get(timeout=max(0, deadline-time.perf_counter()))
        observe(*msg)
        if msg[1] == F8:
            return msg[0]
        if msg[1] != (0xFE,):
            raise ValueError(f"Expected one F8; received {msg!r}")
    raise TimeoutError("missing F8")


def summarize_ns(ns):
    values = sorted(n / 1_000_000 for n in ns)
    return {"median_ms": statistics.median(values), "p99_ms": values[math.ceil(.99 * len(values)) - 1],
            "max_ms": values[-1], "min_ms": values[0]}


def assess(rows):
    if len(rows) != COUNT:
        raise ValueError(f"Cannot calibrate from {len(rows)} pairs; expected {COUNT}")
    latency = []
    api = []
    for index, (seq, send, returned, received) in enumerate(rows):
        if seq != index or send > returned or received < send or (index and rows[index - 1][3] >= send):
            raise ValueError(f"Missing, premature or overlapping pair at {index}")
        latency.append(received - send)
        api.append(returned - send)
    median = statistics.median(latency)
    return {"pairs": len(rows), "reference": "host send entry to receive callback, through the DIN link between the recorded endpoints",
            "path_delay": summarize_ns(latency),
            "absolute_jitter_around_median": summarize_ns([abs(x - median) for x in latency]),
            "absolute_interarrival_minus_intersend": summarize_ns([abs(b - a) for a, b in zip(latency, latency[1:])]),
            "send_call_duration": summarize_ns(api),
            "latency_population_sd_ms": statistics.pstdev(latency) / 1e6,
            "p99_definition": "nearest rank; no outliers trimmed; no division by two"}


def measure(outdir, tx_name, rx_name, opening=live_midi, now=time.perf_counter_ns, pause=time.sleep):
    rows = []
    with (outdir / "m2-events.csv").open("x", newline="") as raw, (outdir / "m2-pairs.csv").open("x", newline="") as pair_file:
        events, pairs = csv.writer(raw), csv.writer(pair_file)
        events.writerow(["action", "qpc_ns", "bytes_hex", "backend_delta_s"])
        pairs.writerow(["sequence_zero_based", "send_entry_qpc_ns", "send_return_qpc_ns", "rx_callback_qpc_ns"])
        def observe(stamp, message, delta):
            events.writerow(["receive", stamp, bytes(message).hex(), delta])
        with opening(tx_name, rx_name) as (tx, inbox, ports):
            write_json(outdir / "ports.json", ports)
            check_quiet(inbox, QUIET_NS / 1e9, observe)
            due = now()
            for i in range(COUNT):
                # A single outstanding indistinguishable F8. Do not hide loss by retrying.
                pause(max(0., (due - now()) / 1e9))
                check_quiet(inbox, 0., observe)
                sent = now()
                tx.send_message([0xF8])
                returned = now()
                events.writerow(["send", sent, "f8", ""])
                events.writerow(["return", returned, "", ""])
                received = get_f8(inbox, observe)
                row = (i, sent, returned, received)
                rows.append(row)
                pairs.writerow(row)
                due = max(sent + PERIOD_NS, received + 2_000_000)
            check_quiet(inbox, QUIET_NS / 1e9, observe)
    return assess(rows)


def selftest():
    rows = [(i, i * PERIOD_NS, i * PERIOD_NS + 100_000, i * PERIOD_NS + 1_000_000 + i % 3 * 100_000) for i in range(COUNT)]
    clean = assess(rows)
    assert clean["pairs"] == COUNT and clean["path_delay"]["median_ms"] == 1.1
    assert clean["absolute_interarrival_minus_intersend"]["max_ms"] == .2
    for bad in (rows[:-1], [*rows[:-1], rows[-2]], [(0, 10, 11, 9), *rows[1:]]):
        try:
            assess(bad)
        except ValueError:
            continue
        raise AssertionError("invalid pair sequence accepted")
    inbox = queue.SimpleQueue()
    inbox.put((0, (0xfe,), 0.))
    check_quiet(inbox, 0, lambda *_: None)
    inbox.put((0, (0xfe,), 0.))
    inbox.put((1, F8, .001))
    assert get_f8(inbox, lambda *_: None) == 1
    inbox.put((0, F8, 0.))
    try:
        check_quiet(inbox, 0, lambda *_: None)
    except ValueError:
        pass
    else:
        raise AssertionError("unsolicited F8 accepted")
    from tempfile import TemporaryDirectory
    class FakeOut:
        tick = 0
        def __init__(self):
            self.inbox = queue.SimpleQueue()
        def send_message(self, msg):
            self.inbox.put((self.tick + 1_000_000, tuple(msg), .02))
            self.tick += 100_000
        def sleep(self, seconds):
            self.tick += round(seconds * 1e9)
    fake = FakeOut()
    @contextlib.contextmanager
    def open_fake(tx, rx):
        yield fake, fake.inbox, {"send": tx, "receive": rx}
    with TemporaryDirectory() as temp:
        root = Path(temp)
        summary = measure(root, "sender", "receiver", open_fake, lambda: fake.tick, fake.sleep)
        assert json.loads((root / "ports.json").read_text()) == {"send": "sender", "receive": "receiver"}
        assert summary["pairs"] == COUNT and summary["path_delay"]["max_ms"] == 1.
        with (root / "m2-events.csv").open() as raw:
            assert sum(1 for _ in raw) == 1 + COUNT * 3
    print("PASS mock end-to-end: 10,000 matched F8s and 30,000 raw rows; missing/duplicate/premature/unsolicited rejected. No device was enumerated.")


def prepare_run(outdir):
    gate = os.environ.get("SOUNDCRAFT_ACCEPTANCE_RUN")
    if not gate:
        raise RuntimeError("Start the run with environment.py run; live MIDI was not opened")
    root = Path(gate).resolve(strict=True)
    outdir = outdir.resolve()
    if root not in outdir.parents:
        raise ValueError("The MIDI evidence directory must be a new subdirectory of the wrapper run")
    outdir.mkdir(exist_ok=False, parents=True)
    return outdir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["plan", "selftest", "run"])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--tx", help="Exact Windows output port for the transmitting interface")
    parser.add_argument("--rx", help="Exact Windows input port for the other interface")
    args = parser.parse_args()
    if args.mode == "plan":
        print("M-2: 10,000 single-flight F8s, ~3.5 minutes; .25 s quiet at each end. Full host→DIN→host latency, zero split-leg assumption.")
    elif args.mode == "selftest":
        selftest()
    else:
        if args.out is None:
            parser.error("--out must be a new evidence directory")
        if not args.tx or not args.rx or {port_family(args.tx), port_family(args.rx)} != {"UM-ONE", "Model 12"}:
            parser.error("Select the physical UM-ONE and Model 12 on opposite ends")
        directory = prepare_run(args.out)
        stats = measure(directory, args.tx, args.rx)
        write_json(directory / "m2-result.json", {"status": "candidate; valid only with successful outer environment check", **stats})
        print(json.dumps(stats, ensure_ascii=False))


def port_family(name):
    if "model 12" in name.casefold():
        return "Model 12"
    if re.fullmatch(r"um-one(?: \d+)?", name.casefold()):
        return "UM-ONE"
    return None


if __name__ == "__main__":
    main()

