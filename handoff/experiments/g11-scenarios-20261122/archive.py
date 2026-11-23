from pathlib import Path
import subprocess, os, json, sys
d=Path(__file__).resolve().parent
rows={1662:d.parent/'g11-beat-clock',1663:d/'mtc-tree',1669:d.parent/'g11-storage-clock-follow'}
for pr,repo in rows.items():
    def git(*args):
        return subprocess.run(['git','-c','core.autocrlf=true',*args], cwd=repo, capture_output=True,check=True).stdout
    assert git('rev-parse','HEAD').decode().strip()==json.loads((d/f'pr-{pr}.json').read_text(encoding='utf-8-sig'))['headRefOid']
    changed=git('diff','--name-only','HEAD').decode().splitlines()
    new=git('ls-files','--others','--exclude-standard').decode().splitlines()
    assert all(p.startswith(('crates/','apps/')) and p.endswith('.rs') for p in changed+new)
    patch=git('diff','--binary','HEAD','--',*changed)
    for f in new:
        p=subprocess.run(['git','-c','core.autocrlf=true','diff','--binary','--no-index','--','/dev/null',f],cwd=repo,capture_output=True); assert p.returncode==1
        patch+=p.stdout
    (d/f'local-tests-{pr}.patch').write_bytes(patch)
    # Verify against a temporary private index populated directly from the unchanged PR tree.
    index=d/f'index-check-{pr}'; env=dict(os.environ,GIT_INDEX_FILE=str(index))
    subprocess.run(['git','read-tree','HEAD'],cwd=repo,env=env,check=True)
    subprocess.run(['git','apply','--cached','--check',str(d/f'local-tests-{pr}.patch')],cwd=repo,env=env,check=True)
    index.unlink()
    print(pr,len(changed)+len(new),len(patch))
