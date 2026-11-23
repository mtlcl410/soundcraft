"""Frame the independent C++ ASIO client's measurements with the same physical MIDI clock ruler."""
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path[:0] = [str(root/"midi"), str(root/"audio")]
from midi_path import live_midi
from wire_source import mtc, source
from m1 import np

def save(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf8")

def histogram(run, bounds, hz):
    dtype = np.dtype([("qpc", "<i8"), ("pos", "<u8"), ("flags", "<i4"), ("index", "<i4")])
    path = run/"callbacks.bin"
    count = path.stat().st_size // dtype.itemsize
    buf = np.memmap(path, mode="r", dtype=dtype, shape=(count,))
    t0, t1 = (v*hz//1_000_000_000 for v in bounds)
    lo,hi = np.searchsorted(buf["qpc"],[t0,t1])
    data = buf[lo:hi]
    dt = np.diff(data["qpc"].astype("int64"))*1000/hz
    edges = [0,2,4,7,10,50,200,240,260,float("inf")]
    return dict(callbacks=len(data), intervals=len(dt), bins=np.histogram(dt,bins=edges)[0].tolist(),
                median_ms=float(np.median(dt)) if len(dt) else None,
                mean_ms=float(np.mean(dt)) if len(dt) else None,
                min_ms=float(min(dt)) if len(dt) else None, max_ms=float(max(dt)) if len(dt) else None,
                invalid_position=int(np.count_nonzero((data["flags"] & 2)==0)),
                position_jumps=int(np.count_nonzero(np.diff(data["pos"].astype("int64"))!=256)),
                buffer_index_repeats=int(np.count_nonzero(np.diff(data["index"])==0)))

def measure(run, key, inbox, hz):
    part = run/key
    part.mkdir()
    while not inbox.empty():
        inbox.get_nowait()
    before=time.perf_counter_ns()
    try:
        source(part,"Model 12 MIDI",mtc("30",1))
    except Exception as err:
        save(part/"midi-error.json",str(err))
        time.sleep(max(0,9.2-(time.perf_counter_ns()-before)/1e9))
    time.sleep(.5)
    wire=[]
    with (part/"rx.csv").open("x",newline="") as f:
        out=csv.writer(f)
        out.writerow(["qpc_ns","hex"])
        while not inbox.empty():
            stamp,msg,_=inbox.get_nowait()
            out.writerow([stamp,bytes(msg).hex()])
            if msg[0]==0xf1: wire.append(stamp)
    bounds = [wire[0],wire[-1]] if len(wire)==960 else [before+1_200_000_000,before+9_191_666_667]
    result=histogram(run,bounds,hz)|dict(qpc_ns=bounds, qf=len(wire), wire_bound=len(wire)==960)
    save(part/"histogram.json",result)
    return result

def normal_window(h):
    return (h["intervals"]>=1400 and h["mean_ms"] is not None and abs(h["mean_ms"]-256/48)<0.27
            and h["bins"][7]==0 and h["invalid_position"]==0 and h["position_jumps"]==0)

def reopen_stream(run, process, sequence, mode):
    name=f"reopen-{sequence}"
    tmp=run/(name+".partial")
    tmp.write_text(mode+"\n",encoding="ascii")
    tmp.rename(run/(name+".request"))
    start=time.monotonic()
    while not (run/(name+".json")).is_file():
        if process.poll() is not None or time.monotonic()-start>25:
            raise RuntimeError(f"ASIO {mode} reopen did not complete (exit {process.poll()})")
        time.sleep(.1)
    answer=json.loads((run/(name+".json")).read_text())
    if answer["pid"]!=process.pid: raise RuntimeError("Process changed")
    return answer

def main(run, reopen=False):
    exe=root/"audio/build/storage-sdk"/("storage-sdk-reopen.exe" if reopen else "storage-sdk.exe")
    save(run/"build.json",dict(executable=str(exe),sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
         host_source_sha256=hashlib.sha256((root/"audio/storage_sdk_player.cpp").read_bytes()).hexdigest()))
    with (run/"player.log").open("xb") as log:
        p=subprocess.Popen([str(exe)],cwd=run,stdout=log,stderr=log)
        try:
            limit=time.monotonic()+20
            while not (run/"callbacks.bin").exists() or (run/"callbacks.bin").stat().st_size<24*120:
                if p.poll() is not None or time.monotonic()>limit:
                    raise RuntimeError(f"Native callbacks unavailable: exit {p.poll()}")
                time.sleep(.2)
            m=json.loads((run/"native.json").read_text())
            assert m["sample_rate"]==48000 and m["buffer_frames"]==256 and m["preferred"]==256
            save(run/"device-start.json",m)
            hist={}
            request_no=0
            with live_midi(rx_name="UM-ONE") as (_, inbox, _):
                hist["baseline"]=measure(run,"baseline",inbox,m["qpc_hz"])
                if not hist["baseline"]["intervals"]:
                    raise RuntimeError("No baseline intervals")
                if reopen and not normal_window(hist["baseline"]):
                    raise RuntimeError("Initial stream cadence is not nominal")
                for cycle in range(1,4):
                    save(run/f"ready-{cycle}.json", dict(qpc_ns=time.perf_counter_ns()))
                    while not (run/f"restored-{cycle}").is_file():
                        if p.poll() is not None: raise RuntimeError(f"Native player ended: {p.returncode}")
                        time.sleep(.3)
                    time.sleep(2)
                    name=f"post-{cycle}"
                    hist[name]=measure(run,name,inbox,m["qpc_hz"])
                    if reopen:
                        for mode in ("stream","driver"):
                            request_no+=1
                            reply=reopen_stream(run,p,request_no,mode)
                            name=f"after-{mode}-{cycle}"
                            if not reply["error"]:
                                hist[name]=measure(run,name,inbox,m["qpc_hz"])
                                if normal_window(hist[name]): break
                            else: save(run/(name+"-error.json"),reply)
                        save(run/"partial-histograms.json",hist)
            save(run/"histograms.json",hist)
        finally:
            (run/"finish").touch()
            try: code=p.wait(timeout=12)
            except subprocess.TimeoutExpired:
                p.terminate(); p.wait(); raise
        if code: raise RuntimeError(f"Native ASIO player exit {code}")
        ending=json.loads((run/"end.json").read_text())
        save(run/"device-end.json",dict(device=m["device"],sample_rate=ending["sample_rate"],buffer_frames=ending["preferred"]))

if __name__=="__main__":
    main(Path(os.environ["SOUNDCRAFT_ACCEPTANCE_RUN"]),reopen="--reopen" in sys.argv[1:])
