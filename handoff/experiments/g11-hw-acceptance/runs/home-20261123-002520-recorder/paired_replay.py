from pathlib import Path
import hashlib,json,subprocess,sys,os
p=Path(__file__).resolve().parent
root=p.parents[1]
repo=root/'h4a-follow-candidate'
target=repo/'crates/playback/src/mtc/tests.rs'
original=target.read_bytes()
with_module=original+b'\n#[cfg(test)]\nmod recorder_paired_diagnostic { include!(r"'+str((p/'paired.rs').resolve()).encode()+b'"); }\n'
env=os.environ|{'SC_FULL_TAKE_DATA':str(p/'paired-inputs.txt'),'CARGO_TARGET_DIR':str(root/'target-follow-confirm')}
try:
 target.write_bytes(with_module)
 with (p/'paired.log').open('wb') as f:
  result=subprocess.run([os.environ['COMSPEC'],'/d','/c',str(root.parent/'g11-a10-recovery/run.cmd'),'test','--offline','-j','4','-p','soundcraft-playback','--lib','replay_same_wire_with_and_without_stopped_locate','--','--nocapture'],cwd=repo,env=env,stdout=f,stderr=subprocess.STDOUT)
 result.check_returncode()
finally:
 if target.read_bytes()==with_module:target.write_bytes(original)
 else:raise RuntimeError('Simultaneous diagnostics edit; retained contents')
assert b'1 passed' in (p/'paired.log').read_bytes()
print('diagnostic source restored',hashlib.sha256(original).hexdigest())
