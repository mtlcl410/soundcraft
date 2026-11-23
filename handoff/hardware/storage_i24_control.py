"""Local main + I24 STORAGE diagnostic. Keep one duplex stream throughout."""
import csv
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from manual_run import cmd, hw, live_midi, mtc, save, source
from m1 import np
from storage_cycle import tone


def intervals(run, start_ns, end_ns):
    intervals_ms = []
    segments = []
    for path in sorted((run / "driver").glob("epoch-*.json")):
        m = json.loads(path.read_text())
        n, hz = m["buffer"], m["qpc_frequency"]
        dtype = np.dtype([("pos", "<u8"), ("system", "<u8"), ("qpc", "<u8"),
                          ("serial", "<u8"), ("flags", "<i4"), ("n", "<u4"), ("pcm", "V" + str(8*n))])
        raw = path.with_suffix(".bin")
        count = raw.stat().st_size // dtype.itemsize
        if not count:
            continue
        blocks = np.memmap(raw, mode="r", dtype=dtype, shape=(count,))
        lo, hi = np.searchsorted(blocks["qpc"], [start_ns * hz / 1e9, end_ns * hz / 1e9], side="left")
        b = blocks[lo:hi]
        if len(b):
            times = np.diff(b["qpc"].astype("int64")) * 1000 / hz
            intervals_ms.extend(times.tolist())
            segments.append(dict(epoch=path.stem, callbacks=len(b), meta=m,
                last_qpc_ns=round(int(b["qpc"][-1])*1e9/hz),
                sample_jumps=int(np.count_nonzero(np.diff(b["pos"].astype("int64")) != n)),
                sequence_skips=int(np.count_nonzero(np.diff(b["serial"]) != 1))))
    edges = [0, 2, 4, 7, 10, 50, 200, 240, 260, float("inf")]
    return dict(segments=segments, intervals=len(intervals_ms),
        bins=np.histogram(intervals_ms, bins=edges)[0].tolist(),
        min_ms=min(intervals_ms, default=None), max_ms=max(intervals_ms, default=None),
        median_ms=float(np.median(intervals_ms)) if intervals_ms else None)


def take(run, port, inbox, label):
    part = run / label
    part.mkdir()
    while not inbox.empty():
        inbox.get_nowait()
    cmd(port, "transport.stop")
    cmd(port, "transport.rtz")
    cmd(port, "transport.play")
    start = time.perf_counter_ns()
    try:
        source(part, "Model 12 MIDI", mtc("30", 1))
    except Exception as exc:
        # Loss of the auxiliary MIDI endpoint must not suppress the ASIO measurement.
        save(part / "midi-error.json", str(exc))
        time.sleep(max(0, 9.2 - (time.perf_counter_ns()-start)/1e9))
    time.sleep(.3)
    packets = []
    with (part / "rx.csv").open("x", newline="") as f:
        rows = csv.writer(f)
        rows.writerow(["qpc_ns", "hex"])
        while not inbox.empty():
            stamp, msg, _ = inbox.get_nowait()
            rows.writerow([stamp, bytes(msg).hex()])
            if msg[0] == 0xf1:
                packets.append(stamp)
    bounds = [packets[0], packets[-1]] if len(packets)==960 else [start+1_200_000_000, start+9_191_666_667]
    save(part / "window.json", dict(qpc_ns=bounds, qf=len(packets), wire_bound=len(packets)==960))
    if label == "baseline":
        time.sleep(1)
        h = intervals(run, *bounds)
        save(part / "initial-histogram.json", h)
        if not h["segments"] or not all(s["meta"]["buffer"]==256 and s["meta"]["sample_rate"]==48000 for s in h["segments"]):
            raise RuntimeError("Baseline has no verified 48 kHz / 256 native callbacks")


def run(folder):
    manifest = json.loads((hw/"audio/build/0d490c68-build.json").read_text())
    save(folder/"build.json", manifest)
    driver = folder/"driver"
    driver.mkdir()
    settings = folder/"private-settings"
    settings.mkdir()
    wav = folder/"a4-at-5s.wav"
    tone(wav)
    with socket.socket() as socket_:
        socket_.bind(("127.0.0.1", 0))
        port = socket_.getsockname()[1]
    env = os.environ | dict(SOUNDCRAFT_NO_PREFS="1", SOUNDCRAFT_CONFIG_DIR=str(settings),
                            SC_ASIO_EVIDENCE=str(driver), SC_ASIO_RETURN_INDEX="8")
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    with (folder/"application.log").open("xb") as log:
        proc = subprocess.Popen([manifest["exe"], "--control", str(port)], cwd=folder, env=env,
                                stdout=log, stderr=log, startupinfo=si)
        try:
            for _ in range(180):
                if proc.poll() is not None:
                    raise RuntimeError("Application exited")
                try:
                    cmd(port, "transport.status")
                    break
                except OSError:
                    time.sleep(.25)
            cmd(port, "session.new", name="ASIO control", sample_rate=48000)
            cmd(port, "file.import_audio", path=str(wav), new_tracks=True, at=0)
            t = cmd(port, "track.new", kind="audio", name="Silent capture")["tracks"][0]
            cmd(port, "mix.mute", tracks=[t], value=True)
            device = cmd(port, "ui.audio_device", system="ASIO", input="Model Mixer ASIO",
                         output="Model Mixer ASIO", sample_rate=48000, buffer_size=256)
            save(folder/"configuration.json", device)
            if device["device"]["silent"]:
                raise RuntimeError(device)
            cmd(port, "mix.record_arm", tracks=[t], value=True)
            with live_midi(rx_name="UM-ONE") as (_, inbox, _):
                take(folder, port, inbox, "baseline")
                meta = json.loads((driver/"epoch-0.json").read_text())
                state = dict(device="Model Mixer ASIO", sample_rate=meta["sample_rate"], buffer_frames=meta["buffer"])
                save(folder/"device-start.json", state)
                for i in range(1, 4):
                    save(folder/f"ready-{i}.json", dict(qpc_ns=time.perf_counter_ns()))
                    limit = time.monotonic()+1800
                    while not (folder/f"restored-{i}").is_file():
                        if time.monotonic() > limit:
                            raise TimeoutError("Panel operation still pending")
                        time.sleep(.3)
                    time.sleep(2)
                    take(folder, port, inbox, f"post-{i}")
            cmd(port, "transport.stop")
            cmd(port, "mix.record_arm", tracks=[t], value=False)
            cmd(port, "ui.audio_device", system=None, input=None, output=None, buffer_size=None)
            time.sleep(.7)
            last = json.loads(max(driver.glob("epoch-*.json"),key=lambda x:x.stat().st_mtime_ns).read_text())
            save(folder/"device-end.json", dict(device="Model Mixer ASIO", sample_rate=last["sample_rate"], buffer_frames=last["buffer"]))
            results = {}
            for label in ["baseline", "post-1", "post-2", "post-3"]:
                win = json.loads((folder/label/"window.json").read_text())
                results[label] = intervals(folder, *win["qpc_ns"]) | win
            save(folder/"histograms.json", results)
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=15)


if __name__ == "__main__":
    run(Path(os.environ["SOUNDCRAFT_ACCEPTANCE_RUN"]))
