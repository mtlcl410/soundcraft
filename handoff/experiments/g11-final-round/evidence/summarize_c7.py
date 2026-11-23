from pathlib import Path
import json,re
ev=Path(__file__).resolve().parent
work=ev.parent.parent
state=json.loads((ev/'c7-idle-comparison.json').read_text('utf8'))
assert state.get('done')
oldfile=work/'g11-scenarios-20261122'/'c7-final.log'
def values(text):
    return {int(x[0]): x[1:] for x in re.findall(r'C7 inserts=(\d+) tracks=150 actual_wall_s=(\S+) pcm_peak=(\S+) blocks=1500 budget_ms=(\S+) render_host_budget_median_pct=(\S+) p95_pct=(\S+) max_pct=(\S+) software_deadline_misses=(\d+) QF=(\d+) acquired=(\S+) lock_losses=(\d+)',text)}
old=values(oldfile.read_text(encoding='utf8-sig'))
rows=[]
for r in state['attempts']:
    if not r['quiet_run']: continue
    i=r['inserts']
    log=Path(r['log'])
    wall,pcm,budget,med,p95,mx,miss,qf,lock,lost=values(log.read_text('utf8'))[i]
    rows.append((i,old[i][6],miss,old[i][4],p95,med,mx,qf,lock,lost,pcm,r['quiet_8s']['system_percent'],log.name))
out=['# C-7 idle render reference','',
  'Replayed the original standalone C-7 binary and its 150-track project. Each run rendered 1,500 blocks of 128 samples at 48 kHz under generated MTC. The render budget was 2.667 ms per block. The same executable produced the earlier simultaneous-build reference.','',
  'Original executable SHA-256 `'+state['sha256']+'`. Each accepted run followed an eight-second host CPU sample at or below 12.5% of 12 logical CPUs, with no compiler processes at launch or observed during recording.','',
  '| Inserts | Earlier misses | Idle misses | Earlier p95 budget | Idle p95 budget | Idle median budget | Idle maximum budget | Quarter frames | Lock acquired | Lock losses | PCM peak | Host CPU before | Raw output |',
  '|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|---:|---:|---|']
for i,oldmiss,miss,oldp95,p95,med,mx,qf,lk,lost,peak,load,f in rows:
    out.append(f'| {i} | {oldmiss} | {miss} | {oldp95}% | {p95}% | {med}% | {mx}% | {qf} | {lk} | {lost} | {peak} | {load}% | [{f}]({f}) |')
out+=['','This benchmark times the software render on a monotonic host clock. External ASIO, Model 12 main output and acoustic playback are outside its measurement path.','',
   ('One or more configurations still exceeded the block budget during this idle reference. Track callback cost separately as mixer performance. The existing G-11 feature PRs need no performance patch on this evidence.' if any(int(r[2]) for r in rows) else 'All measured render blocks completed within the 2.667 ms budget in this idle reference.'),'',
   'Original command runs the ignored test with `SCENARIO_C7_INSERTS` set separately to 0, 2 and 6.','',
   '```text','load-bench.exe scenario_c7_chase --ignored --nocapture --test-threads=1','```','',
   '[Earlier simultaneous-build reference](../../g11-scenarios-20261122/c7-final.log) · [Idle acquisition and host metadata](c7-idle-comparison.json)','']
(ev/'C7-idle-reference.md').write_text('\n'.join(out),encoding='utf8')
