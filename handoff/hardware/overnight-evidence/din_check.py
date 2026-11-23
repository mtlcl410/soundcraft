"""Quiet DIN round trip: no notes, transport commands or audio device access."""
import csv, json, statistics, sys, time
from pathlib import Path
out = Path(__file__).resolve().parent
sys.path.insert(0, str(out.parent / "midi"))
from midi_path import live_midi, check_quiet, get_f8
rows = []
for source, dest in [("UM-ONE", "Model 12 MIDI"), ("Model 12 MIDI", "UM-ONE")]:
    with live_midi(source, dest) as (tx, inbox, ports):
        check_quiet(inbox, 0.35, lambda *_: None)
        for pulse in range(1200):
            t = time.perf_counter_ns()
            tx.send_message([0xf8])
            end = get_f8(inbox, lambda *_: None)
            rows.append([source, dest, pulse, t, end, (end-t)/1000])
            time.sleep(0.012)
        check_quiet(inbox, .15, lambda *_: None)
    with (out/"din.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sender","receiver","ordinal","host_send_ns","host_receive_ns","roundtrip_us"])
        writer.writerows(rows)
    v = sorted(r[-1] for r in rows if r[0] == source)
    print(ports, len(v), "p50 / p95 / max us:", statistics.median(v), v[(len(v)*95+99)//100-1], v[-1], flush=True)
