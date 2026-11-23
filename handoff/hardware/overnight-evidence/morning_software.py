"""Use different target directories per PR layer; start the combined layer after the ASIO build."""
from pathlib import Path
import subprocess,sys,time,os,json
a=Path(__file__).resolve().parent; d=a.parent
results={}
for tag,folder,target,crate,options in [
    ('beat','overnight-beat-only','g11-verify-beat-target','soundcraft-playback',['--','--test-threads=2']),
    ('mtc','overnight-mtc-only','g11-verify-mtc-target','soundcraft-playback',['--','--test-threads=2']),
    ('follow','overnight-g11','g11-follow-target','soundcraft-playback',['--','--test-threads=2']),
    ('grid','overnight-g11','g11-follow-r3-target','soundcraft-ui-egui',['app::clock_follow','--','--include-ignored','--test-threads=1','--nocapture'])
]:
    if tag=='grid':
        for _ in range(900):
            if (d/'audio/build/4cfaf099-build.json').exists():break
            time.sleep(2)
    with (a/(f'morning-final-{tag}.log')).open('xb') as f:
        results[tag]=subprocess.run([os.environ['COMSPEC'],'/d','/c',str(d.parent/'g11-a10-recovery/run.cmd'),'test','--offline','-p',crate,'--lib',*options],
                          cwd=d/folder,env=os.environ|{'CARGO_TARGET_DIR':str(d.parent/target)},stdout=f,stderr=subprocess.STDOUT).returncode
    (a/'morning-software-progress.json').write_text(json.dumps(results))
(a/'morning-software-finished.json').write_text(json.dumps(results))
