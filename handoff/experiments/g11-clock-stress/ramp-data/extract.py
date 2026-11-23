import re,csv,sys
from pathlib import Path
d=Path(__file__).resolve().parent
rows=[];summary=[]
for name in (sys.argv[1:] or ['baseline.actual','always.actual','track.actual','quadratic.actual','final']):
 p=d/(name+'.log')
 if not p.exists():continue
 text=p.read_text(encoding='utf-8-sig')
 for line in text.splitlines():
  if 'RAMP d=' not in line or 'samples=' not in line:continue
  meta,values=line[line.index('RAMP d=')+5:].split('samples=',1)
  m=dict(pair.split('=',1) for pair in meta.split());dlt=float(m['d']);j=int(m['jitter'])
  nums=[int(v) for v in re.findall(r'-?\d+',values)]
  assert len(nums)==int(m['hits']),(m,len(nums))
  peak=max(abs(x) for x in nums);i=next(i for i,v in enumerate(nums) if abs(v)==peak)
  summary.append((name,dlt,j,len(nums),f'{peak/48:.5f}',i,nums[i],m['last'],m['false_steps'],m.get('adaptive',''),m['locked_jump'],m['estimator_bpm_error'],m['fitted_stamp_error_ms']))
  rows.extend((name,dlt,j,k,v,round(v/48,6),96) for k,v in enumerate(nums))
if rows:
 for name,head,values in [('ramp-eighths.csv',['variant','delta_bpm','jitter_us','eighth_index','signed_samples','signed_ms','verified_burst_frames'],rows),('ramp-summary.csv',['variant','delta_bpm','jitter_us','checked_onsets','peak_abs_ms','peak_index','peak_signed_samples','tail_onset_signed_samples','false_step_count','ramp_confirmed_pulses','max_bpm_jump_after_first_beat','peak_estimator_bpm_error','peak_fitted_stamp_error_ms'],summary)]:
  with (d/name).open('w',encoding='utf8',newline='') as f:w=csv.writer(f);w.writerow(head);w.writerows(values)

