"""Inject a tempo change and loss into a real USB -> DIN loop and independently sample the follower."""
import argparse
import json
from pathlib import Path
import re
import statistics
import sys
import threading
import time

from desktop_sync import cmd
from round4_clock_follow import MESSAGES, summarize

HERE = Path(__file__).resolve().parent


def inject(sequence, pause, mark):
    def clocks(bpm, count):
        start = time.perf_counter()
        for i in range(count):
            pause(max(0, start + i*60/(24*bpm) - time.perf_counter()))
            sequence([0xf8])
    mark("120_bpm")
    sequence([0xf2, 0, 0])
    sequence([0xfa])
    clocks(120, 145)
    mark("clock_loss")
    pause(1.1)
    mark("explicit_stop")
    sequence([0xfc])
    pause(0.35)
    mark("backward_spp")
    sequence([0xf2, 12, 0])
    pause(0.35)
    mark("100_bpm_while_stopped")
    clocks(100, 49)
    mark("100_bpm_continue")
    sequence([0xfb])
    clocks(100, 121)
    mark("final_stop")
    sequence([0xfc])
    pause(0.65)
    mark("end")


def assess(rows, markers, policy, raw_name):
    def during(begin, end, lag=0):
        return [r for r in rows if "follow" in r and markers[begin]+lag <= r["at_ns"] < markers[end]]
    def median_bpm(d):
        vals=[r["follow"]["estimated_bpm"] for r in d if r["follow"].get("state")=="Locked" and r["follow"].get("estimated_bpm")]
        return statistics.median(vals) if vals else None
    early = during("120_bpm","clock_loss",1_000_000_000)
    loss = during("clock_loss","explicit_stop",400_000_000)
    rewind = during("backward_spp","100_bpm_while_stopped")
    warm = during("100_bpm_while_stopped","100_bpm_continue",200_000_000)
    late = during("100_bpm_continue","final_stop",1_000_000_000)
    stop = during("final_stop","end",250_000_000)
    bpm1,bpm2=median_bpm(early),median_bpm(late)
    wire = sorted([r for r in rows if r.get("tap")==raw_name],key=lambda r:r["at_ns"])
    control=[r["raw"] for r in wire if r["raw"][0] != 0xf8]
    spp_positions=[r["transport"]["position"] for r in rewind if not r["transport"]["playing"]]
    earlier=[r["transport"]["position"] for r in early]
    checks={
        "transport_wire":control==[[0xf2,0,0],[0xfa],[0xfc],[0xf2,12,0],[0xfb],[0xfc]],
        "clock_wire":sum(r["raw"]==[0xf8] for r in wire)==315,
        "lock_120":bpm1 is not None and abs(bpm1-120)<1,
        "loss_policy":any(r["follow"]["state"]==("Coasting" if policy=="coast" else "Stopped")
                          and r["transport"]["playing"]==(policy=="coast") for r in loss),
        "backward_stopped_locate":bool(spp_positions and earlier and spp_positions[-1]<max(earlier)),
        "stopped_clocks_do_not_play":bool(warm) and all(not r["transport"]["playing"] for r in warm),
        "continue_100":bpm2 is not None and abs(bpm2-100)<1,
        "explicit_stop":any(not r["transport"]["playing"] and r["follow"]["state"]=="Stopped" for r in stop)
    }
    return {"checks":checks,"measured_locked_bpm":[bpm1,bpm2],"stopped_locate_position":spp_positions[-1] if spp_positions else None,
            **summarize(rows)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run",action="store_true")
    p.add_argument("--port",type=int)
    p.add_argument("--input",default="UM-ONE")
    p.add_argument("--output",default="Model 12 MIDI")
    p.add_argument("--directory",type=Path)
    p.add_argument("--source-head",default="104a9fc")
    a=p.parse_args()
    if not a.run:
        print("Plan only: each of coast and stop-on-loss uses 145 clocks at 120 BPM, a 1.1 s loss, Stop, backward SPP=12, 49 stopped clocks at 100 BPM and Continue + 121 clocks at 100 BPM, Stop.")
        return
    if not a.port or not a.directory: p.error("--port and a new --directory are required")
    a.directory.mkdir(parents=True,exist_ok=False)
    orig=cmd(a.port,"setup.midi_sync_status")
    if cmd(a.port,"transport.status")["playing"] or orig["settings"]["enabled"] or cmd(a.port,"setup.mtc_output").get("enabled"):
        raise RuntimeError("Use the stopped silent acceptance project with generator and Beat Clock output disabled")
    slot=orig["clock_follow"]
    if cmd(a.port,"setup.mtc").get("online"):
        raise RuntimeError("MTC chase is online")
    sys.path.insert(0,str(HERE/"capture-deps"))
    import rtmidi
    out=rtmidi.MidiOut()
    tap=rtmidi.MidiIn()
    def index(device, label):
        match=[i for i,n in enumerate(device.get_ports()) if n==label or re.sub(r" [0-9]+$","",n)==label]
        if len(match)!=1:raise ValueError((label,device.get_ports()))
        return match[0]
    output_idx=index(out,a.output)
    input_idx=index(tap,a.input)
    results={}
    try:
        out.open_port(output_idx)
        tap.ignore_types(sysex=True,timing=False,active_sense=True)
        tap.open_port(input_idx)
        for policy in ("coast","stop"):
            cmd(a.port,"setup.midi_clock_follow",enabled=False)
            cmd(a.port,"setup.midi_clock_follow",input=a.input,enabled=True,loss_policy=policy)
            before=cmd(a.port,"setup.midi_sync_status")
            rows=[]
            end=threading.Event()
            markers={}
            def poll():
                while not end.is_set():
                    ts=time.perf_counter_ns()
                    try:
                        f=cmd(a.port,"setup.midi_clock_follow");tr=cmd(a.port,"transport.status")
                        rows.append({"at_ns":ts,"reply_ns":time.perf_counter_ns(),"follow":f,"transport":tr})
                    except (ValueError,OSError) as e:
                        rows.append({"at_ns":ts,"poll_error":str(e)})
                    end.wait(0.05)
            def recv(event,_):
                if event[0] and event[0][0] in MESSAGES:
                    rows.append({"at_ns":time.perf_counter_ns(),"tap":a.input,"raw":list(event[0])})
            def mark(label):markers[label]=time.perf_counter_ns()
            tap.set_callback(recv)
            worker=threading.Thread(target=poll,daemon=True)
            worker.start()
            try:
                inject(out.send_message,time.sleep,mark)
            finally:
                end.set();worker.join(20);tap.cancel_callback()
            result=assess(rows,markers,policy,a.input)
            result.update({"source":"script -> Model 12 USB MIDI -> Model 12 MIDI OUT -> Roland UM-ONE DIN -> SoundCraft",
                           "head":a.source_head,"policy":policy,"markers":markers,"before":before,"after":cmd(a.port,"setup.midi_sync_status")})
            with (a.directory/(policy+".jsonl")).open("x",encoding="utf8") as file:
                for row in sorted(rows,key=lambda r:r["at_ns"]):
                    print(json.dumps(row,ensure_ascii=False),file=file)
            results[policy]=result
            print(policy, result["checks"],flush=True)
    finally:
        if out.is_port_open():
            out.send_message([0xfc]);out.close_port()
        if tap.is_port_open():tap.close_port()
        if slot.get("enabled") or slot.get("input"):
            cmd(a.port,"setup.midi_clock_follow",input=slot["input"],enabled=slot["enabled"],loss_policy=slot["loss_policy"])
        else:
            cmd(a.port,"setup.midi_clock_follow",input=None,enabled=False,loss_policy=slot["loss_policy"])
    (a.directory/"summary.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf8")
    if not all(all(r["checks"].values()) for r in results.values()):raise SystemExit(1)


if __name__=="__main__":
    main()
