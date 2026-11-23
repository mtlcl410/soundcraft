from assess import mono,matches,here
import json,numpy as np
ref=mono(here/'monitor-reference.wav')
cr=json.loads((here/'monitor-reference-analysis.json').read_text())['crash_recording_frames'][0]
results={}
for mode in ('monitor-reference','chorus-from-8','precise-64'):
    j=json.loads((here/(mode+'.json')).read_text());x=mono(here/(mode+'.wav'))
    t=j['begin'];times=np.array([b[0] for b in j['blocks']]);bidx=int(np.abs(times-t).argmin());first=int(sum(b[1] for b in j['blocks'][:bidx]))
    if mode=='monitor-reference': first=cr
    start=max(0,first-4800)
    x=x[start:first+48000]
    ab=np.abs(x); aud=np.flatnonzero(ab>35);res={'first_loud_relative_host_ms': round((int(aud[0])+start-first)/48,1) if len(aud) else None}
    for offset in [0,10,25,50,75,105,140,180,205,250,280,320,500]:
        i=cr+offset*48; tpl=ref[i:i+1200]
        if not np.any(tpl):continue
        scores=matches(x,tpl); k=int(scores.argmax());res[str(offset)]=[round(float(scores[k]),3),round((k+start-first)/48,1)]
    results[mode]=res
print(json.dumps(results,indent=1))
(here/'first-second-comparison.json').write_text(json.dumps(results,indent=2))