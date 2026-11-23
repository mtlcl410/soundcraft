from pathlib import Path
import re, csv, ast, statistics, math
d = Path(__file__).parent
def read(p):
    t = p.read_bytes()
    return t.decode("utf-16" if t.startswith(b"\xff\xfe") else "utf-8-sig", errors="replace")
fields = r"bpm=(\d+) frames=(\d+) ms=(\d+) clicks=(true|false)"
def key(b,f,l,c):
    return (int(b),int(f),int(l),"click" if c=="true" else "note")
groupdata = {}
for b,f,l,c,starts,lengths in re.findall("reference "+fields+r" starts=(\[[^\]]+\]) lengths=(\[[^\]]+\])",read(d/"summary.log")):
    groupdata[key(b,f,l,c)] = ast.literal_eval(starts),ast.literal_eval(lengths)
assert len(groupdata)==36, len(groupdata)
old = {}
for b,f,l,c,obs,expect,intact,delta in re.findall("lead "+fields+r" count=(\d+)/(\d+) intact=(\d+) samples=(\[[^\]]+\])",read(d/"red.log")):
    old[key(b,f,l,c)] = ast.literal_eval(delta)
assert len(old)==36
summaries = []
records = []
for b,f,l,c,policy,obs,expect,intact,delta in re.findall("lead "+fields+r" policy=(Hard|Predict) count=(\d+)/(\d+) intact=(\d+) samples=(\[[^\]]+\])",read(d/"summary.log")):
    k=key(b,f,l,c)
    bpm,buf,lead,voice=k
    batch=ast.literal_eval(delta)
    if policy == "Hard": assert batch==old[k], (k,batch,old[k])
    starts,lengths=groupdata[k]
    count,expected,intact=map(int,(obs,expect,intact))
    assert len(batch)==count==expected==intact==len(starts)==len(lengths)
    small=str(buf*bpm*24<48_000*60).lower()
    row=dict(bpm=bpm,buffer_samples=buf,presentation_lead_ms=lead,buffer_shorter_than_pulse=small,policy=policy,voice=voice)
    ms=lambda value: round(value/48,6)
    for i,(ideal,ds,num) in enumerate(zip(starts,batch,lengths),1):
        records.append({**row,"ordinal":i,"eighth_index":i*(2 if voice=="click" else 1),"reference_on_sample":ideal,"actual_on_sample":ideal+ds,"delta_samples":ds,"delta_ms":ms(ds),"reference_last_nonzero_sample":ideal+num-1,"actual_last_nonzero_sample":ideal+ds+num-1,"verified_full_waveform_samples":num})
    summaries.append({**row,"onsets":count,"expected":expected,"missing":max(0,expected-count),"extra":max(0,count-expected),"complete_waveforms":intact,
    "first_offbeat_ms":ms(batch[0]) if voice=="note" else "","first_beat_ms":ms(batch[1 if voice=="note" else 0]),
    "min_ms":ms(min(batch)),"max_ms":ms(max(batch)),"median_ms":ms(statistics.median(batch)),
    "worst_signed_after_first_beat_ms":ms(max(batch[2 if voice=="note" else 1:],key=abs))})
def write(name, rows):
    with (d/name).open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
assert len(summaries)==72 and len(records)==1728
write("device-lead-steady-onsets.csv",records)
write("device-lead-steady.csv",summaries)
for s in ("true","false"):
    for policy in ["Hard","Predict"]:
        g=[r for r in summaries if r["buffer_shorter_than_pulse"]==s and r["policy"]==policy]
        print(s,policy,len(g)//2,min(r["min_ms"] for r in g), max(r["max_ms"] for r in g), "first offbeat range",min(r["first_offbeat_ms"] for r in g if r["voice"]=="note"),max(r["first_offbeat_ms"] for r in g if r["voice"]=="note"), "first beat range",min(r["first_beat_ms"] for r in g),max(r["first_beat_ms"] for r in g),"intact waveforms",sum(r["complete_waveforms"] for r in g))
