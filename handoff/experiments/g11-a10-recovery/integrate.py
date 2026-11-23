from pathlib import Path
import shutil,subprocess,os
d=Path(__file__).resolve().parent
env=dict(os.environ,GIT_AUTHOR_NAME='mtlcl410',GIT_AUTHOR_EMAIL='2368091+mtlcl410@users.noreply.github.com',GIT_COMMITTER_NAME='mtlcl410',GIT_COMMITTER_EMAIL='2368091+mtlcl410@users.noreply.github.com')
prev=None
for n in ['beat','mtc','follow']:
 r=d/n
 def git(*a,check=True):
  return subprocess.run(['git','-c','core.autocrlf=true','-C',str(r),*a],check=check,capture_output=True,env=env)
 def out(*a):return git(*a).stdout.decode().strip()
 tracked=out('diff','--name-only').splitlines()
 new=out('ls-files','--others','--exclude-standard').splitlines()
 assert new==['crates/playback/src/beat_clock/recovery.rs']
 names=tracked+new
 assert names and all(f.startswith('crates/playback/src/') for f in names)
 expected={f:(r/f).read_bytes() for f in names}
 mtc_files=[f for f in names if '/mtc' in f]
 if prev:
  git('restore','--worktree','--',*tracked)
  for f in new:
   assert (r/f).read_bytes()==expected[f]
   (r/f).unlink()
  merged=git('merge','--no-ff','--no-commit',prev,check=False)
  if merged.returncode and not out('diff','--name-only','--diff-filter=U'):raise RuntimeError(merged.stderr)
  for f,data in expected.items():
   if n=='mtc' and f in mtc_files:continue
   (r/f).write_bytes(data)
  git('add','--',*names)
  git('diff','--cached','--check')
  git('commit','-m','Merge Beat Clock timing recovery from #1662' if n=='mtc' else 'Merge compensated Clock and MTC recovery from #1663')
  if n=='mtc':
   for f in mtc_files:(r/f).write_bytes(expected[f])
 if n!='follow':
  git('add','--',*names)
  git('diff','--cached','--check')
  git('commit','-m','Repay missed Beat Clock ticks evenly within one quarter note' if n=='beat' else 'Resume MTC at the live frame after device timing loss')
 assert not out('status','--porcelain')
 # Verify the committed blobs, ignoring checkout line-ending conversion.
 for f,data in expected.items():
  assert git('show','HEAD:'+f).stdout.replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n'),f
 prev=out('rev-parse','HEAD')
 print(n,prev)
