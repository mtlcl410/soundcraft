"""Keep the red test on the previous checkout; run the same acceptance on the candidate."""
import os,subprocess,sys
from pathlib import Path
a=Path(__file__).resolve().parent;d=a.parent;gw=d/'morning-device-grid';before=d/'overnight-g11'
os.environ['CARGO_TARGET_DIR']=str(d.parent/'g11-follow-r3-target')
def run(tree,name,selectors):
    with (a/(name+'.log')).open('wb') as f:
        return subprocess.run([os.environ['COMSPEC'],'/d','/c',str(d.parent/'g11-a10-recovery/run.cmd'),'test','--offline','-p','soundcraft-ui-egui','--lib',*selectors],cwd=tree,stdout=f,stderr=subprocess.STDOUT).returncode
base=before/'crates/ui-egui/src/app/clock_follow.rs';old=base.read_bytes()
test=(gw/'crates/ui-egui/src/app/clock_follow/device_time.rs').read_text()
tests=test.split('#[cfg(test)]')[1]
tests=tests.replace('let mut device = DeviceTime::default();','').replace('let start = Instant::now();','')
tests=tests.replace('let measured = device.project(wire,Some((0,0)),rate,|| Some((1,start + Duration::from_secs(seconds as u64),actual_sample.round())));','let measured = wire;')
tests=tests.replace('mod tests {','mod hardware_rate_regression {')
patched=old+b'\n#[cfg(test)]\n'+tests.encode()+b'\n'
try:
    base.write_bytes(patched)
    red=run(before,'device-grid-red',['next_external_downbeat_uses_physical_samples','--','--nocapture'])
finally:
    if base.read_bytes()==patched:base.write_bytes(old)
green=run(gw,'device-grid-green',['next_external_downbeat_uses_physical_samples','--','--nocapture'])
if green==0:
    all_rc=run(gw,'device-grid-all',['app::clock_follow','--','--include-ignored','--test-threads=1','--nocapture'])
else:all_rc=-1
print(red,green,all_rc)
sys.exit(0 if red==101 and green==all_rc==0 else 1)
