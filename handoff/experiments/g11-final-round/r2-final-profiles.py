import os,subprocess,sys,re,json
from pathlib import Path
d=Path(__file__).resolve().parent
w=d/'follow';ev=d/'evidence'
env=os.environ|{'CARGO_TARGET_DIR':str(d.parent/'g11-verify-beat-target'),'SOUNDCRAFT_PACKET_TRACE':'1','SOUNDCRAFT_SWEEP_DIR':str(ev/'r2-final-device')}
(ev/'r2-final-device').mkdir(exist_ok=True)
r=Path(d.parent/'g11-a10-recovery/run.cmd')
with (ev/'r2-actual-build.log').open('wb') as f:
    subprocess.run([str(r),'test','--locked','-p','soundcraft-ui-egui','--lib','--no-run','-j','2'],cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
exe=re.findall(r'Executable unittests[^\n]+\((.+?\.exe)\)',(ev/'r2-actual-build.log').read_text(encoding='utf8'))[-1]
jobs=[('onset','first_usb_batches_mid_song',False),('phases','trailing_packed_slowdowns',False),('long','twenty_full_length_dj_tracks',True),('short','clock_follow::tests::',False),('8hours','eight_hours_of_clock_flutter',True),('10mins','ten_minutes_of_coalesced',True),('sweep','slowdown_device_phase_sweep',True)]
codes=[]
for name,which,ignored in jobs:
  args=[exe,which,'--nocapture','--test-threads=2']
  if ignored:args+=['--ignored']
  with (ev/f'r2-actual-{name}.log').open('wb') as f:
    rc=subprocess.run(args,cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT).returncode;codes.append(rc)
  print(name,rc,flush=True)
sys.exit(int(any(codes)))

