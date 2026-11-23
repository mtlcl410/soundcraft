"""Measure each STORAGE cycle in one unchanged SoundCraft process."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time

script_dir = Path(__file__).resolve().parent
prior = script_dir.parent
root = Path(os.environ.get("SOUNDCRAFT_STORAGE_TAKE_DIR", script_dir)).resolve()
sys.path[:0] = [str(prior), str(prior.parent), str(prior.parent / "capture-deps")]
from desktop_sync import cmd, rpc
from partition import Audio, ref, wire
import rtmidi


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def setup(exe):
    root.mkdir(parents=True, exist_ok=True)
    project = root / "smu-model12-chase.scraft"
    shutil.copyfile(prior / project.name, project)
    if (root / "process.json").exists():
        raise RuntimeError("A test instance has already been registered")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    preferences = root / "preferences"
    preferences.mkdir(exist_ok=True)
    env = dict(os.environ, SOUNDCRAFT_NO_PREFS="1", SOUNDCRAFT_CONFIG_DIR=str(preferences),
               RUST_LOG="warn,soundcraft_playback::stream_recovery=info",
               VST3_PATH="E:/S-MU2000-windows-x64/plugins", CLAP_PATH="E:/S-MU2000-windows-x64/plugins",
               S_MU2000_ROMS="E:/S-MU2000-windows-x64/roms")
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    with (root / "desktop.log").open("xb") as log:
        child = subprocess.Popen([exe, "--control", str(port), project], cwd=root, env=env,
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, startupinfo=startup)
    with open(exe, "rb") as binary, project.open("rb") as song:
        save(root / "process.json", dict(pid=child.pid, port=port, exe=str(exe),
             sha256=hashlib.file_digest(binary, "sha256").hexdigest(),
             project_sha256=hashlib.file_digest(song, "sha256").hexdigest()))
    for _ in range(180):
        if child.poll() is not None:
            raise RuntimeError("Desktop exited")
        try:
            cmd(port, "transport.status")
            break
        except OSError:
            time.sleep(.25)
    else:
        raise RuntimeError("No control socket")
    audio = cmd(port, "ui.audio_device")
    assert "Model 12" in audio["device"]["name"] and audio["device"]["sample_rate"] == 48000, audio
    assert not cmd(port, "transport.status")["recording"]
    mtc = cmd(port, "setup.mtc", input="UM-ONE", online=True, freewheel="frames", freewheel_frames=8)
    assert mtc["online"] and mtc["input"] == "UM-ONE"
    save(root / "armed.json", dict(audio=audio, mtc=mtc))


def replay():
    packets = []
    source = prior.parent / "h-mtc-sd-20261121-211205" / "take1-wire.jsonl"
    for line in source.read_text().splitlines():
        stamp, name, data = json.loads(line)
        if name.startswith("UM-ONE") and data[0] == 0xF1:
            if packets and stamp - packets[0][0] > 6_500_000_000:
                break
            packets.append((stamp, data))
    assert len(packets) == 781
    output = rtmidi.MidiOut()
    ports = [idx for idx, name in enumerate(output.get_ports()) if name.startswith("Model 12 MIDI ")]
    assert len(ports) == 1, output.get_ports()
    output.open_port(ports[0])
    locate = [240, 127, 127, 1, 1, 96, 0, 0, 0, 247]
    try:
        output.send_message(locate)
        time.sleep(.8)
        start = time.perf_counter() + .12
        for stamp, data in packets:
            target = start + (stamp - packets[0][0]) / 1e9
            remaining = target - time.perf_counter()
            if remaining > .001:
                time.sleep(remaining - .0007)
            while time.perf_counter() < target:
                pass
            output.send_message(data)
        time.sleep(.6)
        output.send_message(locate)
        time.sleep(.6)
    finally:
        output.close_port()


def state(port):
    status = rpc(port, "ui.inspect", {})
    sync = cmd(port, "setup.midi_sync_status")
    return dict(qpc=time.perf_counter(), status=status["status"], device=status["audio_device"],
                diagnostic=sync["output"], chase=sync["mtc_chase"])


def watch(port, label):
    until = time.monotonic() + 1200
    with (root / (label + ".jsonl")).open("x", encoding="utf-8", buffering=1) as f:
        while time.monotonic() < until and not (root / (label + ".end")).exists():
            try:
                row = state(port)
                row["mounted_model12_sd"] = Path("H:/MTR/040208_0011").is_dir()
            except Exception as err:
                row = dict(qpc=time.perf_counter(), error=str(err))
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            time.sleep(.17)


def take(port, name):
    dest = root / name
    dest.mkdir()
    snapshot = state(port)
    save(dest / "before.json", snapshot)
    assert "Model 12" in snapshot["device"], snapshot
    active = cmd(port, "transport.status")
    assert not active["playing"] and not active["recording"]
    flag = dest / "end"
    jobs = []
    try:
        for title, args in [
            ("midi", [prior / "tap.exe", dest / "ready", flag, dest / "wire.csv"]),
            ("render", [prior / "phase-audio.exe", "loop", dest / "loop", flag])
        ]:
            with (dest / (title + ".log")).open("wb") as log:
                jobs.append(subprocess.Popen(args, stdout=log, stderr=log))
        for _ in range(100):
            assert all(p.poll() is None for p in jobs)
            if (dest / "ready").exists() and (dest / "loop.csv").exists():
                break
            time.sleep(.08)
        else:
            raise RuntimeError("Capture not ready")
        observer = threading.Thread(target=watch, args=(port, name + "-samples"))
        observer.start()
        try:
            replay()
        finally:
            (root / (name + "-samples.end")).touch()
            observer.join()
    finally:
        flag.touch()
        for p in jobs:
            p.wait(timeout=15)
    after = state(port)
    save(dest / "after.json", after)
    assert after["chase"]["locks"] > snapshot["chase"]["locks"]
    (anchor, jitter, count, frame), = wire(dest)
    assert count == 781 and frame == 2, (count, frame)
    audio = Audio(dest / "loop")
    matches = [m for ch in range(2) if (m := audio.find(anchor + 5, ch, ref))]
    t, score = max(matches, key=lambda m: abs(m[1]), default=(0, 0))
    result = dict(render_delay_ms=round((t - anchor - 5) * 1000, 3) if abs(score) > .9 else None,
                  correlation=round(score, 5), qf_count=count, qf_scatter_ms=jitter,
                  anchor_qpc=anchor, source_file="take1-wire.jsonl")
    save(dest / "result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    if mode == "setup":
        setup(Path(args[0]).resolve(strict=True))
    else:
        port = json.loads((root / "process.json").read_text())["port"]
        if mode == "take":
            take(port, args[0])
        elif mode == "watch":
            watch(port, args[0])
        elif mode == "state":
            print(json.dumps(state(port), ensure_ascii=False))
        elif mode == "snapshot":
            label, = args
            save(root / (label + ".json"), state(port))
            rpc(port, "ui.screenshot", dict(path=str(root / (label + ".png"))))
        elif mode == "offline":
            print(cmd(port, "setup.mtc", online=False))
            print(cmd(port, "transport.status"))
