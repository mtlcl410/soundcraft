from pathlib import Path
import subprocess
d=Path(__file__).resolve().parent
clock=(d/'repayment-test.rs').read_text(encoding='utf-8-sig').strip()
for n in ['beat','mtc','follow']:
 f=d/n/'crates/playback/src/sync_output_tests.rs'
 s=f.read_text();a=s.index('#[test]\nfn recovered_clock_repositions');b=s.index('#[test]\nfn a_missed_timing_gap',a)
 f.write_bytes((s[:a]+clock+'\n\n'+s[b:]).encode())
for n in ['beat','mtc','main']:
 r=d/(n+'-red')
 subprocess.run(['git','-C',str(d/n),'worktree','add','--detach','--quiet',str(r),'HEAD'],check=True)
 for file,test in [('sync_output_tests.rs',clock),('mtc_sync_output_tests.rs',(d/'mtc/crates/playback/src/mtc_sync_output_tests.rs').read_text().split('#[test]\nfn recovered_mtc_locates')[1])]:
  f=r/'crates/playback/src'/file
  if not f.exists():continue
  if file.startswith('mtc'):test='#[test]\nfn recovered_mtc_locates'+test
  with f.open('ab') as out:out.write(('\n'+test+'\n').encode())
