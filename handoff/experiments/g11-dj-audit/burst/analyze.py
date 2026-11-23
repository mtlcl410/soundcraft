from pathlib import Path
import csv, sys, re, statistics as st
from collections import defaultdict
D=Path(__file__).parent
log=(D/'render.log').read_text(encoding='utf-8',errors='replace')
assert 'test result: ok. 1 passed' in log
base=['from_bpm','to_bpm','transition_pulse','packet_timing','counterexample']
hits=defaultdict(list); pulses=defaultdict(list); assigned=defaultdict(list)
for line in log.splitlines():
    tag=line.partition(',')[0]
    if tag not in ['PULSE','HIT','ASSIGN']: continue
    a=line.split(',')[1:]; key=tuple(a[:5]); v=a[5:]
    if tag=='HIT': hits[key].append(v)
    elif tag=='PULSE': pulses[key].append(v)
    else: assigned[key].append(v)
assert len(hits)==16
assert hits.keys()==assigned.keys()
with (D/'eighths.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f);w.writerow(base+['eighth_index','expected_sample','pcm_onset_sample','delta_samples','voice_samples','reference_match','delta_ms'])
    for k,rows in assigned.items():
        for row in sorted(rows,key=lambda x:int(x[0])): w.writerow([*k,*row,round(int(row[3])/48,6) if row[3] else ''])
with (D/'pulse_windows.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f);w.writerow(base+['pulse','ideal_us','arrival_us','render_pos_samples','edit_guard_sample','fit_bpm','confirming_intervals','grouped','recovering','first_offbeat_on_grid_samples'])
    for k,rows in pulses.items():
        for row in rows: w.writerow([*k,*row])
with (D/'summary.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f);w.writerow(base+['pcm_hits','expected','missing_expected_slots','extra_attacks_or_unmatched','malformed','dropouts','early_step_confirmations','post_step_confirmations','confirmation_pulse_offset','expected_first_ms','first_actual_ms','first_signed_error_ms','second_signed_error_ms','step_confirm_ms','first_group_distinguishes_rate_ms','edit_guard_ms','first_error_after_confirmation_ms'])
    for k,rows in hits.items():
        a,b,t,mode,cmp=k;c=int(t)//12; pulses_case={int(r[0]):r for r in pulses[k]};start=float(pulses_case[int(t)][1]);
        case=re.search('CASE '+re.escape('-'.join(k))+r' missing=(\d+) extra=(\d+) damaged=(\d+) dropouts=(\d+) early_steps=(\d+) confirmations=(\d+) first=(.*)',log)
        assert case, k
        m,e,d,drop,pre,step=map(int,case.groups()[:6]); cf=case.group(7); offset=int(re.search(r'\((\d+)',cf)[1]) if cf!='None' else None
        assert len(rows)==(c+17)-m+e
        first=int(rows[c+1][2])/48-start/1000 if not (m or e) else None
        firsterr=int(rows[c+1][3])/48 if not (m or e) else None
        seconderr=int(rows[c+2][3])/48 if not (m or e) else None
        confirmation=(int(pulses_case[int(t)+offset][2])-start)/1000 if offset is not None and offset<=26 else None
        know=(int(pulses_case[int(t)+3][2])-start)/1000 if mode=='VariableBurst' else None
        def r(x): return round(x,6) if x is not None else ''
        w.writerow([*k,len(rows),c+17,m,e,d,drop,pre,step,offset,30000/int(b),r(first),r(firsterr),r(seconderr),r(confirmation),r(know),30,r(first-confirmation) if first is not None and confirmation is not None else ''])
