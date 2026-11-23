from assess import mono,matches,here
import json,numpy as np
source=here.parent/'chorus-latency-1675-fixed'
sample=json.loads((source/'monitor-reference-analysis.json').read_text())['crash_recording_frames'][0]+24000
needle=mono(source/'monitor-reference.wav')[sample:sample+2000]
data=json.loads((here/'split.json').read_text())
for mode,v in data.items():
 expected=int(v['spp']==64)
 assert v['ticks']==144 and v['digital_count']==expected and v['main_count']==expected,(mode,v)
 v['later_music_correlation']=round(float(matches(mono(here/(mode+'.wav')),needle).max()),5)
 assert v['later_music_correlation']>.9,(mode,v)
 print(mode, v['later_music_correlation'],v.get('digital_to_main_ms'))
(here/'final-acceptance.json').write_text(json.dumps(data,indent=2))
