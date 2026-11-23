from partition import *
from itertools import groupby
rows=[]
for folder in ['repeat01','series','series2','series3']:
 path=d/folder
 if not (path/'partition.json').is_file():continue
 for r in json.loads((path/'partition.json').read_text()):
  markers=[m['capture_origin_minus_wire_ms'] for m in r['mic_markers'] if m['capture_origin_minus_wire_ms'] is not None]
  qualified=len(markers)==2 and abs(markers[0]-markers[1])<=2
  rows.append(dict(song=r['song'],batch=folder,start=(round(r['first_qf_label_frames']/30) if r.get('first_qf_label_frames') is not None else None),sd=r['sd_onset_ms'],render=r['render_tap_minus_wire_ms'],capture=round(statistics.mean(markers),3) if qualified else None,composite=r.get('sd_backing_as_seen_on_capture_clock_minus_render_tap_ms')))
def stats(items):
 v=[float(x) for x in items if x is not None]
 return dict(n=len(v),min=round(min(v),3),median=round(statistics.median(v),3),max=round(max(v),3),spread=round(max(v)-min(v),3)) if v else {}
out={'rows':rows}
for batch in ['all']+list(dict.fromkeys(r['batch'] for r in rows)):
 use=rows if batch=='all' else [r for r in rows if r['batch']==batch]
 out[batch]={k:stats([r[k] for r in use]) for k in ['sd','render','capture','composite']}
print(json.dumps(out,indent=2))
(d/'distribution.json').write_text(json.dumps(out,indent=2))
