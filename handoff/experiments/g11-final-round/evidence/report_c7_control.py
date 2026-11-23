from pathlib import Path
import json,re,sys
ev=Path(__file__).resolve().parent
name=sys.argv[1]
meta=ev/f'c7-{name}-comparison.json'; st=json.loads(meta.read_text('utf8')); assert st.get('done')
def parse(s):
  pattern=r'C7 inserts=(\d+) tracks=150 actual_wall_s=(\S+) pcm_peak=(\S+) blocks=1500 budget_ms=(\S+) render_host_budget_median_pct=(\S+) p95_pct=(\S+) max_pct=(\S+) software_deadline_misses=(\d+) QF=(\d+) acquired=(\S+) lock_losses=(\d+)'
  return {int(x[0]):x[1:] for x in re.findall(pattern,s)}
original=parse((ev.parent.parent/'g11-scenarios-20261122'/'c7-final.log').read_text('utf-8-sig'))
runs=[r for r in st['attempts'] if r['quiet_run']]
assert {r['inserts'] for r in runs}=={0,2,6} and all('native-' in r['log'] for r in runs)
out=['# C-7 '+('strict idle' if name=='idle' else 'desktop-load')+' reference','',
 'This is a matched repeat of the original software benchmark on the same 12-logical-CPU Windows workstation. It runs 150 simultaneous mono audio tracks at 48 kHz, with 0, 2, or 6 compressor inserts per track. The harness times 1,500 blocks of 128 samples under generated 25 fps MTC. Its 2.667 ms deadline covers rendering, PCM peak reading, MTC host service, and transport handling.','',
 'The executable SHA-256 is `'+st['sha256']+'`. Each accepted run was observed through a native Windows process snapshot. No compiler, Cargo task or other SoundCraft test process appeared in the eight-second pre-run and post-run windows or during the run. '+('Each accepted run also showed no more than 12.5% total CPU in the preceding eight seconds.' if name=='idle' else 'This group exceeded the strict 12.5% total CPU gate and is a separate desktop-load control.'),'',
 '| Inserts per track | Original misses | Current misses | Original p95 | Current p95 | Current median | Current max | MTC quarter frames | Acquired / losses | PCM peak |',
 '|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|']
for r in runs:
 i=r['inserts'];z=parse(Path(r['log']).read_text('utf8'))[i];old=original[i];out.append(f'| {i} | {old[6]}/1500 | {z[6]}/1500 | {old[4]}% | {z[4]}% | {z[3]}% | {z[5]}% | {z[7]} | {z[8]} / {z[9]} | {z[1]} |')
out+=['','Median, p95 and max are percentages of the block budget. Host CPU below is a percentage of the workstation. Background-process CPU is shown as a percentage of one logical core.','',
 '| Inserts | CPU 8 s before | CPU during | CPU 8 s after | Leading background processes before | Leading background processes after | Raw output |','|---:|---:|---:|---:|---|---|---|']
for r in runs:
 pre,post=r['quiet_8s'],r['after_8s']; f=Path(r['log']).name
 top=lambda a:', '.join(f'{k} {v:.1f}%' for k,v in list(a['top_one_core_percent'].items())[:3])
 out.append(f'| {r["inserts"]} | {pre["system_percent"]}% | {r["system_during_percent"]}% | {post["system_percent"]}% | {top(pre)} | {top(post)} | [{f}]({f}) |')
misses=[int(parse(Path(r['log']).read_text('utf8'))[r['inserts']][6]) for r in runs]
out+=['',('At least one software block missed its deadline. Investigate mixer and host service timing separately from the G-11 transports.' if any(misses) else 'All 4,500 software blocks in this matched reference met the 2.667 ms deadline.'),'',
       '[Final-round local acceptance report](../STATUS.zh-TW.md) · [Desktop-load control](C7-desktop-reference.md) · [Strict idle result](C7-idle-reference.md)']
out+=['','The external ASIO callback, physical MIDI cables and Model 12 main output lie outside this benchmark. A missed software deadline warrants a separate mixer/host timing investigation, including timing the render and host service individually. An audible dropout cannot be inferred from this result.', '',
 'Run once with each of 0, 2 and 6 as `SCENARIO_C7_INSERTS`.','', '```text','load-bench.exe scenario_c7_chase --ignored --nocapture --test-threads=1','```','',
 '[Original simultaneous-build log](../../g11-scenarios-20261122/c7-final.log) · [Workload monitoring, including rejected runs]('+meta.name+')','']
(ev/f'C7-{name}-reference.md').write_text('\n'.join(out),encoding='utf8')
