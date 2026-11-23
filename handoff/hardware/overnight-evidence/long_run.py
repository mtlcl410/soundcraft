"""Run once, with device settings in an isolated SoundCraft config. Always leave a terminal status."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback
a=Path(__file__).resolve().parent;d=a.parent;p=a/'combined-two-hours'
status=a/'combined-two-hours-status.json'
def state(phase,**kv):
    tmp=status.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(phase=phase,time=time.strftime('%Y-%m-%d %H:%M:%S %z'),**kv),indent=2));tmp.replace(status)
try:
    if p.exists():raise RuntimeError('Existing run directory; refusing to overwrite.')
    state('starting',planned_seconds=7200)
    env=os.environ|{'PYTHONPATH':os.pathsep.join(map(str,[d/'audio',d/'midi',d]))}
    with (a/'combined-two-hours.log').open('x') as log:
        cmd=[sys.executable,'-X','utf8',str(d/'environment.py'),'run','--panel',str(d/'panel.json'),'--out',str(p),'--audio','--',sys.executable,'-X','utf8',str(a/'pilot2.py'),'7200']
        proc=subprocess.Popen(cmd,env=env,cwd=d,stdout=log,stderr=subprocess.STDOUT)
        state('running',monitor_pid=proc.pid,planned_seconds=7200)
        rc=proc.wait()
    if (p/'result.json').exists():
        subprocess.run([sys.executable,str(a/'summarize_soak.py'),str(p)],check=True)
    verdict=json.loads((p/'environment-result.json').read_text()) if (p/'environment-result.json').exists() else {}
    if not (p/'window-analysis.json').exists() or rc or not verdict.get('environment_valid'):
        raise RuntimeError(str((rc,verdict)))
    summary=json.loads((p/'window-analysis.json').read_text())
    state('measured',counts_match=summary['counts_match'],dropouts=summary['observed_dropouts'],report=str(p/'RESULT.zh-TW.md'))
except BaseException:
    state('incomplete',error=traceback.format_exc());raise

