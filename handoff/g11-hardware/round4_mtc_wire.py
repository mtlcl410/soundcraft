"""Capture physical USB-to-DIN output on a fresh SoundCraft test instance.

Write raw observations only. Call analyze_round4_mtc_wire.py separately.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from desktop_sync import cmd, rpc

HERE = Path(__file__).resolve().parent
RATES = [("23.976", 24000, 1001), ("24", 24, 1), ("25", 25, 1), ("29.97", 30000, 1001), ("29.97 Drop", 30000, 1001), ("30", 30, 1)]


def calibration_dialogs(port, directory, output, call, log):
    for index, hz in enumerate([96000,48000,96000]):
        call("session.new", name=f"Calibration {index} {hz}", sample_rate=hz)
        if index==0:
            call("setup.mtc_output",port=output,enabled=True,offset_samples=20000)
            call("setup.midi_beat_clock",enabled=True,ports={output:{"enabled":True,"offset_samples":20000}})
        for menu in ["setup.midi_beat_clock","setup.peripherals"]:
            invoke=rpc(port,"ui.menu.invoke",{"id":menu})
            time.sleep(.30)
            snapshot=rpc(port,"ui.inspect",{})
            path=directory/f"calibration-{index}-{hz}-{menu}.png"
            screenshot=rpc(port,"ui.screenshot",{"path":str(path.resolve())})
            log(dialog_case="before-close",rate=hz,menu=menu,invoke=invoke,
                dialog=snapshot.get("dialog",snapshot.get("dialogs")),screenshot=screenshot,file=path.name)
            rpc(port,"ui.key",{"key":"Enter"})
            time.sleep(.30)
            after=rpc(port,"ui.inspect",{})
            if after.get("dialog") or after.get("dialogs"):
                rpc(port,"ui.key",{"key":"Escape"})
            log(dialog_case="after-close",rate=hz,menu=menu,
                dialog=after.get("dialog",after.get("dialogs")),
                mtc=call("setup.mtc_output"),beat=call("setup.midi_beat_clock"),diagnostics=call("setup.midi_sync_status"))
    call("setup.midi_beat_clock",enabled=False)
    call("setup.mtc_output",enabled=False)


def minimized_window(pid):
    import ctypes as c
    from ctypes import wintypes as w
    user=c.windll.user32
    windows=[]
    callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    @callback
    def visit(raw,_):
        handle=w.HWND(raw)
        owner=w.DWORD()
        user.GetWindowThreadProcessId(handle,c.byref(owner))
        if owner.value!=pid or not user.IsWindowVisible(handle):
            return True
        title=c.create_unicode_buffer(512)
        user.GetWindowTextW(handle,title,len(title))
        rect=w.RECT()
        user.GetClientRect(handle,c.byref(rect))
        width,height=rect.right-rect.left,rect.bottom-rect.top
        if width>=300 and height>=200 and title.value:
            windows.append((width*height,title.value,raw))
        return True
    user.EnumWindows(visit,0)
    if not windows:
        raise ValueError("The private desktop has no titled, visible application window")
    named=[row for row in windows if "soundcraft" in row[1].casefold()]
    candidates=sorted(named or windows,reverse=True)
    if len(candidates)>1 and candidates[0][0]==candidates[1][0]:
        raise ValueError(f"Equal-sized private application windows: {candidates}")
    return user,w.HWND(candidates[0][2])


def capture(exe, directory, output, expected_sha, include_dialogs, extra, window_only, native):
    import rtmidi
    directory.mkdir(parents=True, exist_ok=False)
    exe = exe.resolve(strict=True)
    with exe.open("rb") as binary:
        digest = hashlib.file_digest(binary, "sha256").hexdigest()
    if digest.lower() != expected_sha.lower():
        raise ValueError(f"Desktop digest mismatch: {digest}")
    with socket.socket() as bind:
        bind.bind(("127.0.0.1", 0))
        port = bind.getsockname()[1]
    settings = directory / "settings"
    settings.mkdir()
    env = dict(os.environ, SOUNDCRAFT_NO_PREFS="1", SOUNDCRAFT_CONFIG_DIR=str(settings))
    runtime = (directory / "desktop.log").open("xb")
    proc = subprocess.Popen([str(exe), "--control", str(port)], stdout=runtime, stderr=runtime,
                            stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, env=env)
    capture_log = (directory / "capture.jsonl").open("x", buffering=1, encoding="utf-8")
    notes = (directory / "operations.jsonl").open("x", buffering=1, encoding="utf-8")
    def log(**data):
        print(json.dumps(data, ensure_ascii=False), file=notes)
    def call(method, **params):
        start = time.perf_counter_ns()
        response = rpc(port, "engine.execute", {"command":method, "params":params})
        log(command=method, params=params, result=response, start_ns=start, end_ns=time.perf_counter_ns())
        return response
    def window(case, operation, seconds, **meta):
        start = time.perf_counter_ns()
        operation()
        time.sleep(seconds)
        end = time.perf_counter_ns()
        log(window=case, start_ns=start, end_ns=end, **meta)
    def packet(event, _):
        data, delta = event
        print(json.dumps([time.perf_counter_ns(), delta, data]), file=capture_log)
    listener = None
    native_process = None
    try:
        for _ in range(240):
            if proc.poll() is not None:
                raise RuntimeError(f"Desktop exited {proc.returncode}")
            try:
                cmd(port, "transport.status")
                break
            except (OSError, ValueError):
                time.sleep(.25)
        else:
            raise TimeoutError("Desktop private control port")
        call("session.new", name="Physical MTC output verification", sample_rate=48000)
        state = call("setup.session")
        outputs = call("setup.mtc_output", list_ports=True)["ports"]
        if outputs.count(output) != 1:
            raise ValueError(f"Expected exactly one {output!r} output in {outputs}")
        if native:
            ready,stop,file=(directory/name for name in ("tap-ready","tap-stop","tap.csv"))
            native_process=subprocess.Popen([str(HERE/"round4_winmm_qf.exe"),str(ready),str(stop),str(file)],
                    creationflags=subprocess.CREATE_NO_WINDOW,stdin=subprocess.DEVNULL)
            for _ in range(250):
                if ready.exists(): break
                if native_process.poll() is not None: raise RuntimeError(f"Native WinMM tap exit {native_process.returncode}")
                time.sleep(.02)
            else: raise TimeoutError("Native WinMM readiness")
            tap="UM-ONE (native WinMM preallocated buffer)"
        else:
            listener = rtmidi.MidiIn()
            ins = listener.get_ports()
            matches = [i for i,n in enumerate(ins) if n == "UM-ONE" or n.startswith("UM-ONE ")]
            if len(matches) != 1:
                raise ValueError(f"Expected one UM-ONE input in {ins}")
            listener.ignore_types(sysex=False, timing=False, active_sense=True)
            listener.set_callback(packet)
            listener.open_port(matches[0])
            tap=ins[matches[0]]
        log(exe=str(exe), sha256=digest, source_port=output, capture_port=tap,
            fresh_session=state, route=["Model 12 USB MIDI input","Model 12 DIN OUT","Roland UM-ONE DIN input"])
        window("external-source-control", lambda:None, .6)
        call("setup.mtc_output", port=output, enabled=True)
        time.sleep(.25)
        if not window_only:
            window("one-hour-locate", lambda:call("transport.locate", at=48000), .25)
            window("one-hour-start", lambda:call("transport.locate", at=0), .35)
            for rate, num, den in RATES:
                call("setup.session", frame_rate=rate, start_timecode="00:00:00:00")
                call("transport.locate", at=0)
                time.sleep(.2)
                window("rolling", lambda:call("transport.play", **{"from":0}), 2.6, rate=rate, num=num, den=den)
                call("transport.stop")
                time.sleep(.20)
                if rate == "29.97 Drop":
                    for index, label in [(1799,[0,0,59,29]), (1800,[0,1,0,2]), (17981,[0,9,59,29]), (17982,[0,10,0,0])]:
                        at=(index*48000*1001+29999)//30000
                        window("df-full-frame",lambda:call("transport.locate",at=at),.32,at=at,label=label)
            call("setup.session", frame_rate="30", start_timecode="00:00:00:00")
            call("transport.locate", at=0)
            call("setup.midi_beat_clock", enabled=True, ports={output:{"enabled":True,"offset_samples":0}})
            call("setup.mtc_output", enabled=True, port=output, offset_samples=0)
            time.sleep(.45)
            window("shared-start",lambda:call("transport.play",**{"from":0}),.45)
            for step, offset in enumerate([0,240,0]):
                if step:
                    call("setup.mtc_output", offset_samples=offset)
                time.sleep(.45)
                window("shared-steady",lambda:None,1.6,offset=offset)
                call("setup.midi_sync_status")
            window("shared-stop",lambda:call("transport.stop"),.25)
            call("setup.midi_beat_clock",enabled=False)
            call("setup.mtc_output",enabled=False)
        if extra:
            call("setup.mtc_output",port=output,enabled=True,offset_samples=0)
            call("setup.session",frame_rate="30",start_timecode="00:00:00:00")
            user,handle=minimized_window(proc.pid)
            def space():
                if not window_only:
                    return rpc(port,"ui.key",{"key":"Space"})
                # Deliver to this process only. These are Win32 messages, not a physical keyboard.
                if not user.PostMessageW(handle,0x100,0x20,0x00390001):
                    raise OSError("PostMessage(WM_KEYDOWN)")
                time.sleep(.04)
                if not user.PostMessageW(handle,0x101,0x20,0xc0390001):
                    raise OSError("PostMessage(WM_KEYUP)")
            log(transport_input="Win32 PostMessage WM_KEYDOWN/UP VK_SPACE" if window_only else "SoundCraft ui.key Space")
            for i in range(0 if native else 10):
                call("transport.locate",at=0)
                time.sleep(.12)
                window("space-start",space,.55,trial=i+1)
                call("transport.status")
                window("space-stop",space,.22,trial=i+1)
                call("transport.status")
            user,handle=minimized_window(proc.pid)
            user.ShowWindow(handle,6)
            try:
                time.sleep(.2)
                log(window_state="minimized",is_iconic=bool(user.IsIconic(handle)))
                rates=[("30",30,1)]*5 if native else RATES
                for trial,(rate,num,den) in enumerate(rates):
                    call("setup.session",frame_rate=rate,start_timecode="00:00:00:00")
                    call("transport.locate",at=0)
                    time.sleep(.2)
                    window("minimized-rolling",lambda:call("transport.play",**{"from":0}),3.2 if native else 2.1,
                           rate=rate,num=num,den=den,trial=trial+1)
                    if native:
                        call("setup.midi_sync_status")
                    call("transport.stop")
                    time.sleep(.2)
            finally:
                user.ShowWindow(handle,4)
                log(window_state="restored",is_iconic=bool(user.IsIconic(handle)))
            call("setup.mtc_output",enabled=False)
        if include_dialogs:
            try:
                calibration_dialogs(port,directory,output,call,log)
            except (ValueError, OSError,TimeoutError) as e:
                log(dialog_case="error",error=str(e))
    finally:
        try:
            if listener is not None:
                listener.close_port()
            if native_process is not None:
                (directory/"tap-stop").touch()
                code=native_process.wait(timeout=10)
                if code!=0: raise RuntimeError(f"Native tap exit {code}")
                with (directory/"tap.csv").open() as raw:
                    previous=0
                    for row in csv.DictReader(raw):
                        tick,freq,stamp,packed=(int(row[key]) for key in ["tick","frequency","driver_ms","data"])
                        first=packed&255
                        length=3 if first==242 else 2 if first==241 else 1
                        bytes_=[packed>>(8*i)&255 for i in range(length)]
                        print(json.dumps([tick*10**9//freq,(stamp-previous)/1000,bytes_]),file=capture_log)
                        previous=stamp
        finally:
            proc.terminate()
            proc.wait(timeout=10)
            capture_log.close()
            notes.close()
            runtime.close()


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe",type=Path,required=True)
    parser.add_argument("--sha256",required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--port-name",default="Model 12 MIDI")
    parser.add_argument("--calibration-ui",action="store_true")
    parser.add_argument("--extra",action="store_true")
    parser.add_argument("--window-only",action="store_true")
    parser.add_argument("--native-minimized",action="store_true")
    args=parser.parse_args()
    sys.path.insert(0,str(HERE/"capture-deps"))
    capture(args.exe,args.out,args.port_name,args.sha256,args.calibration_ui,args.extra or args.window_only or args.native_minimized, args.window_only or args.native_minimized,args.native_minimized)
