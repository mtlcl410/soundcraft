from pathlib import Path
import subprocess as sp
d=Path.cwd();base=d/'w1662'
def git(w,*args,check=True):
 r=sp.run(['git','-c','user.name=mtlcl410','-c','user.email=2368091+mtlcl410@users.noreply.github.com','-C',str(w),*args],stdout=sp.PIPE,stderr=sp.PIPE,check=check)
 return r.stdout.decode('utf8',errors='replace').strip()
for n,initial,expected in [(1662,'b1a9d50c','7e305842'),(1663,'51773fa','0b22907'),(1669,'d762dfe','095e1ed')]:
 w=d/f'publish{n}'
 git(base,'worktree','add','--detach',str(w),initial)
 if n==1662: git(w,'merge','--squash',expected)
 else:
  git(w,'merge','--no-ff','--no-commit',lower,check=False)
  assert git(w,'rev-parse','MERGE_HEAD')==lower
  git(w,'restore','--source='+expected,'--staged','--worktree','--','.')
 p=w/'docs/midi-input.md';s=p.read_bytes()
 needle=b' Hardware verification of this revision is pending.'
 assert s.count(needle)==1
 p.write_bytes(s.replace(needle,b''))
 git(w,'add','docs/midi-input.md');git(w,'diff','--cached','--check')
 if n==1662:msg='Separate Beat Clock acceptance measurements from the product and CI suite'
 elif n==1663:msg='Merge Beat Clock output packaging into MTC'
 else:msg='Merge MTC packaging into external Beat Clock follow'
 git(w,'commit','-m',msg)
 lower=git(w,'rev-parse','HEAD')
 assert git(w,'diff','--name-only',expected,'HEAD')=='docs/midi-input.md'
 print(n,lower)
