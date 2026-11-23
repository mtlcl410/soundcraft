"""Run and retain each stack member's tests against its exact committed tree."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys

directory = Path(__file__).resolve().parent
number, raw_worktree, raw_target = sys.argv[1:4]
worktree = Path(raw_worktree).resolve()
target = Path(raw_target).resolve()
head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=worktree,text=True).strip()
if subprocess.check_output(['git','status','--porcelain'],cwd=worktree).strip():
    raise SystemExit('Working tree differs from head')
results = directory/'evidence'/f'{number}-{head[:8]}'
results.mkdir(exist_ok=True)
env = os.environ | {'CARGO_TARGET_DIR':str(target),'CARGO_TERM_COLOR':'never'}
runner = str(directory.parent/'g11-a10-recovery'/'run.cmd')
tests = {
    '1662':['soundcraft-playback','soundcraft-ui-egui','soundcraft'],
    '1663':['soundcraft-playback','soundcraft-ui-egui','soundcraft-engine','soundcraft'],
    '1669':['soundcraft-mix','soundcraft-playback','soundcraft-ui-egui','soundcraft-engine','soundcraft'],
}[number]
lint = [c for c in tests if c not in ['soundcraft-engine','soundcraft']]
commands=[]
for crate in tests:
    kind=['--bin','soundcraft'] if crate=='soundcraft' else ['--lib']
    commands.append((crate,['test','--locked','-j','2','-p',crate,*kind,'--','--test-threads=2']))
commands.append(('clippy',['clippy','--locked','-j','2',*[v for c in lint for v in ['-p',c]],'--lib','--tests','--no-deps','--','-D','warnings']))
commands.append(('fmt',['fmt','--all','--','--check']))
rows=[]
for label,args in commands:
    path=results/(label+'.log')
    with path.open('wb') as f:
        rc=subprocess.run(['cmd','/c',runner,*args],cwd=worktree,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=worktree,text=True).strip()!=head or subprocess.check_output(['git','status','--porcelain'],cwd=worktree).strip():
        raise SystemExit('Revision changed during verification')
    log=path.read_text(encoding='utf-8',errors='replace')
    outcome=re.findall(r'test result: [^\r\n]*',log)
    rows.append(dict(head=head,check=label,code=rc,command='cargo '+' '.join(args),result=outcome))
    (results/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(label,rc,outcome,flush=True)
sys.exit(int(any(r['code'] for r in rows)))
