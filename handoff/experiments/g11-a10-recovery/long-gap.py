import sys
from pathlib import Path
d=Path(__file__).resolve().parent
f=d/'follow/crates/playback/src/mtc_sync_output_tests.rs'
snap=d/'mtc-suite-committed.rs'
if 'restore' in sys.argv:
 f.write_bytes(snap.read_bytes())
else:
 snap.write_bytes(f.read_bytes())
 patch=(d.parent/'g11-scenarios-20261122/local-tests-1663.patch').read_text()
 text=patch[patch.index('+#[test]\n+fn scenario_a10_dual'):].split('\ndiff --git',1)[0]
 with f.open('ab') as out:out.write(('\n'+text.replace('\n+','\n')[1:]+'\n').encode())
