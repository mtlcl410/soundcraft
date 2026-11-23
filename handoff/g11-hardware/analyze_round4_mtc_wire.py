"""Decode round-four output evidence offline; publish observations and per-case checks."""
import argparse
import json
import statistics as st
import math
from pathlib import Path


def read(path):
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def full_frame(data):
    if len(data)==10 and data[:5]==[240,127,127,1,1] and data[-1]==247:
        return data[5]>>5, [data[5]&31, *data[6:9]]


def decode_group(messages):
    if [m[2][1]>>4 for m in messages]!=list(range(8)):
        return None
    nibbles=[m[2][1]&15 for m in messages]
    frame,second,minute,hour=[nibbles[i]|nibbles[i+1]<<4 for i in (0,2,4,6)]
    rate=hour>>5
    hour=hour&31
    if not(hour<24 and second<60 and minute<60 and frame<[24,25,30,30][rate]): return None
    if rate==2 and minute%10 and second==0 and frame<2: return None
    index=((hour*60+minute)*60+second)*[24,25,30,30][rate]+frame
    if rate==2:
        mins=hour*60+minute
        index-=2*(mins-mins//10)
    return rate,index


def quant(v,p):
    return sorted(v)[round((len(v)-1)*p)] if v else None


def main(directory,filename="wire-analysis.json"):
    records=read(directory/"operations.jsonl")
    bins=[]
    driver=0
    for host,delta,byte in read(directory/"capture.jsonl"):
        driver+=delta*1e9
        bins.append((host,driver,byte))
    key_method=next((op["transport_input"] for op in records if "transport_input" in op),"SoundCraft ui.key Space")
    out=[]
    checks=[]
    def check(case,name,passed):
        checks.append(dict(case=case,criterion=name,passed=bool(passed)))
    for c in (op for op in records if "window" in op):
        tag=c["window"]
        src=[m for m in bins if c["start_ns"]<=m[0]<=c["end_ns"]]
        decoded=[full_frame(m[2]) for m in src if full_frame(m[2])]
        q=[m for m in src if len(m[2])==2 and m[2][0]==241]
        f8=[m for m in src if m[2][0]==248]
        m=dict(case=tag,**{k:c[k] for k in ["rate","offset","at","trial"] if k in c})
        key=tag+str(c.get("rate",c.get("label","")))
        m["full_frames"]=decoded
        m["qf"]=len(q)
        m["f8"]=len(f8)
        if tag=="external-source-control":
            check(key,"quiet before any generator is enabled",not q and not decoded and not f8)
        if tag=="df-full-frame":
            check(key,"stopped full-frame bytes match expected drop-frame label",(2,c["label"]) in decoded)
        if tag=="one-hour-start":
            check(key,"new session origin is 01:00:00:00",any(v[1]==[1,0,0,0] for v in decoded))
        if tag=="space-start":
            check(f"{key_method} start {c['trial']}","rolling QF starts within 0.5s of key request",
                  bool(q) and (q[0][0]-c["start_ns"])/1e9<=.5 and len(q)>=25)
            m["request_to_first_qf_ms"]=(q[0][0]-c["start_ns"])/1e6 if q else None
        if tag=="space-stop":
            late=[msg for msg in q if msg[0]>=c["start_ns"]+150_000_000]
            check(f"{key_method} stop {c['trial']}","no rolling QF after 150 ms",not late)
        if tag in ["rolling","minimized-rolling","shared-steady"]:
            groups=[(m[0],decode_group(q[i:i+8])) for i,m in enumerate(q[:-7]) if m[2][1]>>4==0]
            continuity=all(((a[2][1]>>4)+1)%8==b[2][1]>>4 for a,b in zip(q,q[1:]))
            m["groups"]=len(groups)
            m["qf_sequence_errors"]=sum(((a[2][1]>>4)+1)%8!=b[2][1]>>4 for a,b in zip(q,q[1:]))
            check(key,"complete ordered QF groups with consecutive two-frame labels",len(groups)>8 and continuity and all(g for _,g in groups) and all(b[1][1]-a[1][1]==2 for a,b in zip(groups,groups[1:])))
            code={"23.976":0,"24":0,"25":1,"29.97":3,"29.97 Drop":2,"30":3}[c.get("rate","30")]
            complete=[g for _,g in groups if g is not None]
            m["incomplete_groups"]=len(groups)-len(complete)
            check(key,"expected wire rate code in all decodable groups",bool(complete) and all(g[0]==code for g in complete))
            for j,label in [(0,"host"),(1,"winmm")]:
                gaps=[(b[j]-a[j])/1e6 for a,b in zip(q,q[1:])]
                m[label]=dict(median_ms=quant(gaps,.5),min_ms=min(gaps,default=None),sub_1ms=sum(v<.999 for v in gaps))
            check(key,"no QF pairs below 1 ms at the WinMM timestamp resolution",len(q)>8 and m["winmm"]["sub_1ms"]==0)
            if groups and all(g for _,g in groups):
                rate=c.get("num",30)/c.get("den",1)
                m["quarter_index_phase_ms"]=st.median(t/1e6-g[1]*1000/rate for t,g in groups)
                if len(groups)>1:
                    m["measured_fps"]=(groups[-1][1][1]-groups[0][1][1])*1e9/(groups[-1][0]-groups[0][0])
                    check(key,"mean frame cadence within 0.5% of configured rate",abs(m["measured_fps"]/rate-1)<.005)
            if tag=="shared-steady":
                beat_gaps=[(b[0]-a[0])/1e6 for a,b in zip(f8,f8[1:])]
                m["clock_median_ms"]=quant(beat_gaps,.5)
                m["clock_interval_errors"]=sum(abs(v-1000/48)>6 for v in beat_gaps)
                check(key,"both protocols received and uninterrupted in stable window",len(f8)>65 and len(q)>155 and m["clock_interval_errors"]==0 and continuity)
                clocks=[x for x in bins if x[2][0]==248]
                by_stamp={event[0]:i for i,event in enumerate(clocks)}
                if f8:
                    m["clock_index_phase_ms"]=st.median(x[0]/1e6-by_stamp[x[0]]*1000/48 for x in f8)
        if tag in ["shared-start","shared-stop"]:
            m["transport"]=[x[2] for x in src if x[2][0] in (250,251,252,242)]
            check(key,"Start/Stop at requested transport transition",[250 if tag=="shared-start" else 252] in m["transport"])
        out.append(m)
    stable=[m for m in out if m["case"]=="shared-steady"]
    offsets=[m["offset"] for m in stable]
    requested_ms=offsets[1]*1000/48000 if len(stable)==3 else None
    if len(stable)==3:
        for field in ["quarter_index_phase_ms","clock_index_phase_ms"]:
            if all(field in r for r in stable):
                before,after,end=[r[field] for r in stable]
                repeat=end-before
                if field=="clock_index_phase_ms":
                    # Calibration can emit SPP + Continue and re-anchor the tick index.
                    # Only a step shorter than half a pulse period is unambiguous without a numbered tick.
                    period_ms=1000/48
                    if abs(requested_ms)>=period_ms/2:
                        check("physical offset","unambiguous sub-half-period Beat Clock calibration",False)
                        continue
                    repeat=math.remainder(repeat,period_ms)
                    observed=math.remainder(after-before-repeat/2,period_ms)
                else:
                    observed=after-(before+end)/2
                out.append(dict(case="physical offset",protocol=field,requested_ms=requested_ms,observed_ms=observed,baseline_repeat_ms=repeat))
                check("physical offset",field+" tracks the calibration",abs(observed-requested_ms)<=2 and abs(repeat)<=3)
            else:
                check("physical offset",field+" captured in all three windows",False)
    if any("window_state" in op for op in records):
        check("minimized","Win32 reports test window minimized",any(op.get("window_state")=="minimized" and op["is_iconic"] for op in records))
        native=any("native WinMM" in op.get("capture_port","") for op in records)
        expected_count=5 if native else 6
        check("minimized",f"{expected_count} captures completed",len([r for r in out if r["case"]=="minimized-rolling"])==expected_count)
    route=next(r for r in records if "exe" in r)
    if not any(op.get("window")=="shared-stop" for op in records):
        report=dict(route=route,measurements=out,checks=checks)
        with (directory/filename).open("x",encoding="utf-8") as f: json.dump(report,f,indent=2)
        print(json.dumps({"checks":len(checks),"failed":[k for k in checks if not k["passed"]]}))
        return not all(k["passed"] for k in checks)
    expected_rates={"23.976","24","25","29.97","29.97 Drop","30"}
    check("coverage","six rates were physically captured",expected_rates=={c.get("rate") for c in out if c["case"]=="rolling"})
    check("coverage","four DF boundary locates captured",sum(c["case"]=="df-full-frame" for c in out)==4)
    status=[op["result"]["output"]["ports"] for op in records if op.get("command")=="setup.midi_sync_status" and op["end_ns"]<next(row["start_ns"] for row in records if row.get("window")=="shared-stop")]
    shared=[ports.get(route["source_port"],{}) for ports in status]
    check("shared port","one active port contains both timing streams at each calibration",
          [p.get("requested_offset_samples") for p in shared]==offsets and
          all(p.get("connected") and p.get("beat_clock_total_us") is not None and p.get("mtc_total_us") is not None for p in shared) and
          all(sum(p["connected"] for p in ports.values())==1 for ports in status))
    report=dict(route=route,measurements=out,checks=checks)
    target=directory/filename
    with target.open("x",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print(json.dumps(dict(measurements=len(out),checks=len(checks),failed=[k for k in checks if not k["passed"]]),ensure_ascii=False))
    return not all(k["passed"] for k in checks)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory",type=Path)
    p.add_argument("--report",default="wire-analysis.json")
    args=p.parse_args()
    raise SystemExit(main(args.directory,args.report))
