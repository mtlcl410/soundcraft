"""Run the two added workflow regressions on the original, uncorrected MTC head."""
from pathlib import Path
import os,subprocess
from owner_probes import test_block
d=Path(__file__).resolve().parent
w=d/'red63'
names=['online_service_reports_why_a_pending_record_was_refused','timecode_retention_respects_automation_switch_and_keeps_both_rulers_on_undo']
for name, path in zip(names,['crates/ui-egui/src/app/mtc.rs','crates/engine/src/cmd/options.rs']):
    p=w/path
    t=p.read_text(encoding='utf8')
    if name not in t:
        at=t.rindex('\n    #[test]')
        p.write_text(t[:at]+'\n'+test_block((d/'mtc'/path).read_text(encoding='utf8'),name)+t[at:],encoding='utf8')
env=os.environ|{'CARGO_TARGET_DIR':str(d.parent/'g11-review3-mtc-fix-target')}
with (d/'evidence'/'F63-extra-unfixed.log').open('wb') as f:
    code=subprocess.run(['cmd','/c',str(d.parent/'g11-a10-recovery'/'run.cmd'),'test','--locked','-j','2','-p','soundcraft-engine','-p','soundcraft-ui-egui','--lib','--no-fail-fast','--',*names],cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
raise SystemExit(code)
