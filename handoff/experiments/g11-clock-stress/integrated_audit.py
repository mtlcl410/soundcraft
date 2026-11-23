from pathlib import Path
import os,sys,shutil,subprocess,re,concurrent.futures
from contextlib import contextmanager
here=Path(__file__).resolve().parent
root=here/'integration'
ts=root/'crates/ui-egui/src/app/clock_follow'
parent=ts.with_suffix('.rs')
wrapper=here.parent/'g11-a10-recovery/run.cmd'
target=here.parent/'g11-follow-r3-target'
env=os.environ|{'CARGO_TARGET_DIR':str(target)}
def run(log,cmd,extra=None):
    with (here/log).open('w',encoding='utf-8') as h:
        r=subprocess.run(cmd,cwd=root,env=env|(extra or {}),stdout=h,stderr=subprocess.STDOUT)
    return (log,r.returncode)
def cargo(log,*args):
    return run(log,['cmd','/c',str(wrapper),*args])
@contextmanager
def overlay():
    original=parent.read_bytes()
    nl=b'\r\n' if b'    mod sampler_song;\r\n' in original else b'\n'
    sentinel=b'    mod sampler_song;'+nl
    assert original.count(sentinel)==1
    probes=['slowdown_sweep','flutter_pcm','performance_scenarios']
    injected=sentinel + nl.join(('    mod '+p+';').encode() for p in probes)+nl
    modified=original.replace(sentinel,injected)
    for p in probes:
        src=(here.parent/'g11-large-tempo' if p=='performance_scenarios' else here)/(p+'.rs')
        shutil.copyfile(src,ts/'tests'/(p+'.rs'))
    parent.write_bytes(modified)
    try:yield
    finally:
        # Keep any intentional independent edits made elsewhere in the file.
        current=parent.read_bytes()
        assert current.count(injected)==1
        parent.write_bytes(current.replace(injected,sentinel))
        for p in probes:
            (ts/'tests'/(p+'.rs')).unlink()
if __name__=='__main__':
    with overlay():
        name,rc=cargo('final-probe-build.log','test','-p','soundcraft-ui-egui','--lib','--no-run')
        if rc:sys.exit(rc)
        line=next(x for x in (here/name).read_text(errors='replace').splitlines() if 'Executable unittests' in x)
        path=re.search(r'\((.*\.exe)\)',line)[1]
        exe=here/'final-probe.exe';shutil.copyfile(path,exe)
    cases=[('flutter-final.log',[str(exe),'audit_eight_hour_pcm','--nocapture'],{'SOUNDCRAFT_FLUTTER_CSV':str(here/'flutter-final.csv')})]
    for p in ['hard','predict']:
        cases.append((f'slow-{p}.log',[str(exe),'audit_slowdown_device_phase_sweep','--nocapture'],{'SOUNDCRAFT_SWEEP_POLICY':p,'SOUNDCRAFT_SWEEP_CSV':str(here/f'slow-{p}.csv')}))
    for name in ['scenario_a2_drop','scenario_edm_eighty','returning_clock_without','eight_hours_of_clock_flutter']:
        args=['--ignored'] if name=='eight_hours_of_clock_flutter' else []
        cases.append((name+'-final.log',[str(exe),name,*args,'--nocapture'],{}))
    with concurrent.futures.ThreadPoolExecutor(3) as pool:
        results=list(pool.map(lambda a:run(*a),cases))
    print(results)
    sys.exit(max(rc for _,rc in results))
