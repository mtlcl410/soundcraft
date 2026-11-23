"""Independent physical wire decoder for this 30 fps forward, zero-origin H-10 exercise."""
import csv
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent.parent / "g11-hardware/capture-deps"))
import numpy as np


def frames(hour_byte, minute, second, frame):
    hour = hour_byte & 31
    if hour_byte >> 5 != 3 or hour >= 24 or minute >= 60 or second >= 60 or frame >= 30:
        raise ValueError("Expected a valid 30 fps non-drop address")
    return 30 * (3600 * hour + 60 * minute + second) + frame


def audit(folder):
    stamps, labels, full_frames = [], [], []
    tail_stamps, piece_stamps = [], []
    two_hour_piece = 2 * 3600 * 30 * 4
    nibbles = []
    with (folder / "egress.csv").open() as fh:
        for row in csv.DictReader(fh):
            message = bytes.fromhex(row["hex"])
            if message.startswith(bytes.fromhex("f07f7f0101")):
                full_frames.append(frames(*message[5:9]))
            if message[0] != 0xf1:
                continue
            index, nibble = divmod(message[1], 16)
            if index != len(nibbles):
                raise ValueError(f"Decoder lost quarter-frame continuity at {row}")
            if index == 0:
                stamps.append(int(row["at_ns"]))
            piece_stamps.append(int(row["at_ns"]))
            nibbles.append(nibble)
            if index == 7:
                f, s, m, h = [nibbles[k] + 16*nibbles[k+1] for k in (0, 2, 4, 6)]
                label = frames(h, m, s, f)
                labels.append(label)
                tail_stamps.extend(t for k,t in enumerate(piece_stamps) if label*4+k >= two_hour_piece)
                piece_stamps.clear()
                nibbles.clear()
    if nibbles or len(labels) < 2:
        raise ValueError("Expected complete quarter-frame groups")
    meta, = (folder / "driver").glob("epoch-*.json")
    cfg = json.loads(meta.read_text())
    rate, buf = cfg["sample_rate"], cfg["buffer"]
    dtype = np.dtype({"names":["pos", "qpc", "flags", "size"], "formats":["<u8","<u8","<i4","<u4"],
                      "offsets":[0,16,32,36], "itemsize":40+8*buf})
    records = np.memmap(meta.with_suffix(".bin"), mode="r", dtype=dtype)
    # Preserve precision, and average 49 adjacent buffer periods to suppress callback scheduling jitter.
    ns = records["qpc"].astype(np.float64) * (1e9 / cfg["qpc_frequency"])
    if not np.all(np.diff(ns) > 0) or not np.all(np.diff(records["pos"]) == buf):
        raise ValueError("ASIO timestamps or positions are discontinuous")
    def device_sample(time_ns):
        t = np.asarray(time_ns, dtype=np.float64)
        right = np.searchsorted(ns, t)
        lo, hi = right - 25, right + 24
        if np.any(lo < 0) or np.any(hi >= len(ns)):
            raise ValueError("Wire edge outside native recording")
        return records["pos"][lo] + (t-ns[lo])/(ns[hi]-ns[lo]) * ((hi-lo)*buf)
    with (folder / "ingress.csv").open() as fh:
        transport = {r["hex"]: int(r["at_ns"]) for r in csv.DictReader(fh) if r["hex"] in ("fa","fc")}
    first, stop = transport["fa"], transport["fc"]
    physical = device_sample(stamps)
    stamp = np.asarray(stamps)
    frame = np.asarray(labels)
    wire_seconds = (stamp-stamp[0])/1e9
    mtc_seconds = (frame-frame[0])/30
    device_seconds = (physical-physical[0])/rate
    def distance(seconds):
        # Compare relative phase of the same type-0 message at both ends; absolute system latency cancels.
        residual = (mtc_seconds-seconds)*1000
        return dict(final_ms=float(residual[-1]),p95_abs_ms=float(np.percentile(abs(residual),95)),
                    p99_abs_ms=float(np.percentile(abs(residual),99)),max_abs_ms=float(np.max(abs(residual))))
    samples = np.diff(device_sample([first,stop]))[0]
    edges=first+np.arange(0, int((stop-first)/60e9)+1)*60_000_000_000
    minute_rates=1e6*(np.diff(device_sample(edges))/(60*rate)-1)
    residual = (mtc_seconds-device_seconds)*1000
    extremes=[]
    overruns=np.flatnonzero(np.diff(ns) > 2*buf*1e9/rate)
    for i in np.flatnonzero(abs(residual)>5):
        nearest = min(overruns, key=lambda k: abs(ns[k+1]-stamp[i])) if len(overruns) else None
        extremes.append(dict(group=int(i),seconds_after_start=(stamps[i]-first)/1e9, res_ms=float(residual[i]),
                             preceding_wire_gap_ms=(stamps[i]-stamps[i-1])/1e6 if i else None,
                             next_wire_gap_ms=(stamps[i+1]-stamps[i])/1e6 if i+1<len(stamps) else None,
                             ms_from_nearest_long_callback_end=(stamps[i]-ns[nearest+1])/1e6 if nearest is not None else None))
    return dict(groups=len(labels), qf=len(labels)*8, first_label=labels[0],last_label=labels[-1],
                non_two_frame_steps=int((np.diff(frame)!=2).sum()),full_frame_addresses=full_frames,
                actual_transport_sample_span=float(samples),device_qf_between_received_start_stop=float(samples*120/rate),
                wall_qf_between_received_start_stop=(stop-first)*120/1e9, device_relative=distance(device_seconds),
                wall_relative=distance(wire_seconds),first_piece_after_start_ms=(stamps[0]-first)/1e6,
                missing_prefix_pieces=labels[0]*4, pieces_at_or_after_two_hours=len(tail_stamps),
                of_these_before_input_stop=sum(t<stop for t in tail_stamps),
                of_these_from_input_stop=sum(t>=stop for t in tail_stamps),
                groups_beyond_5ms=extremes, rate_hz=rate, minute_ppm=minute_rates.tolist(),
                physical_resolution_note="DIN receipt and smoothed buffer-switch timestamps; relative phase only")


if __name__ == "__main__":
    folder = Path(sys.argv[1])
    result = audit(folder)
    print(json.dumps(result, indent=2))
    (folder / "decoded-mtc-vs-device.json").write_text(json.dumps(result, indent=2))
