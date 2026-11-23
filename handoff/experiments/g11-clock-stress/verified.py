import os, sys, subprocess
from pathlib import Path
base=Path(__file__).resolve().parent
root=base/'checks'
env=os.environ|{'CARGO_TARGET_DIR':str(base.parent/'g11-review3-mtc-fix-target')}
wrapper=base.parent/'g11-a10-recovery/run.cmd'
def test(name,*args):
    with (base/(name+'.log')).open('w',encoding='utf8') as f:
        return subprocess.run(['cmd','/c',str(wrapper),*args],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
crates=['-p','soundcraft-mix','-p','soundcraft-playback','-p','soundcraft-ui-egui']
results=[]
results.append(test('integrated-tests','test',*crates,'--lib','--no-fail-fast','--','--nocapture'))
results.append(test('integrated-a4','test','-p','soundcraft-ui-egui','--lib','ten_minutes_of_coalesced','--','--ignored','--nocapture'))
results.append(test('integrated-clippy','clippy',*crates,'--lib','--tests','--no-deps','--','-D','warnings'))
print(results);sys.exit(max(results))
