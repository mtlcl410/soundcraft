from pathlib import Path
import hashlib,json,sys
w=Path(__file__).resolve().parent;d=w.parent
rd=lambda p:json.loads(p.read_bytes())
cases=sys.argv[1:]; timings=rd(w/('timing-'+cases[0]+'.json'));music=rd(w/('music-'+cases[0]+'.json'))
rows=[]
for c in cases:
 real=rd(d/c/'actual.json');t=timings[c];b=t['samples'];assert real['actual']=={'in':[b],'out':[b]}
 r=[v for n,v in music.items() if n.startswith(c+'/')]
 exact=[v for v in r if v['spp']==64];late=[v for v in r if v['spp']==65]
 rows.append(dict(case=c,buffer=b,plugin_ms=t['first_plugin_ms'],callback_ms=t['first_callback_ms'],activation_ms=t['activation_ms'],budget=t['deadline_ms'],exact_once=sum(v['crashes']==1 for v in exact),late_no_replay=sum(v['crashes']==0 for v in late),after_note_correlation_min=min(v['later_corr'] for v in r),waveform_steps_over_32=sum(bool(v['steps_over_32']) for v in r),detected_drop_windows=sum(v['drop_windows'] for v in r),spp_continue_clock_stop_all=True,module=rd(d/c/'loaded-plugin.json')['sha256']))
assert {v['buffer'] for v in rows}=={64,128} and len({v['module'] for v in rows})==1
(w/'final-results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))

