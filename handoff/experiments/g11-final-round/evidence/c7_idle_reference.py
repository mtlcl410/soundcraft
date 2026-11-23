"""Re-run the original standalone C-7 binary; no MIDI or audio driver is opened."""
import hashlib, json, os, psutil, subprocess, time
from datetime import datetime
from pathlib import Path
ev=Path(__file__).resolve().parent
base=ev.parent.parent/'g11-scenarios-20261122'
exe=base/'load-bench.exe'
heavy={'rustc.exe','cargo-clippy.exe','clippy-driver.exe','link.exe','lld-link.exe','cl.exe','rust-lld.exe','clang.exe','clang-cl.exe'}
system=lambda: {proc.pid:(proc.name.lower(),proc.cpu_times.user+proc.cpu_times.system) for info in psutil.process_iter(['pid','name','cpu_times']) if (proc:=info.info) is not None}
# Only CPU time from actively busy compilers matters; long-lived cargo processes waiting on a filesystem lock are idle.
def build_seconds(a,b):
    return sum(max(0,y[1]-a[k][1]) if k in a else y[1] for k,y in b.items() if y[0] in heavy)
def processes():
    out={}
    for p in psutil.process_iter(['pid','name','cpu_times']):
        q=p.info
        if q['cpu_times'] is not None and q['name']:
            out[q['pid']]=(q['name'].lower(),q['cpu_times'].user+q['cpu_times'].system)
    return out
def probe(sec):
    a=processes(); load=psutil.cpu_percent(interval=sec); b=processes()
    return {'system_percent':load,'compiler_seconds':round(build_seconds(a,b),3),'compiler_present':sorted({name for name,_ in b.values() if name in heavy})}
out=ev/'c7-idle-comparison.json'
state={'binary':str(exe),'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'logical_cpus':psutil.cpu_count(),'attempts':[]}
def save(): out.write_text(json.dumps(state,indent=2),encoding='utf-8')
for inserts in (0,2,6):
    while True:
        quiet=probe(8.)
        if quiet['system_percent']>12.5 or quiet['compiler_seconds']>0.12 or quiet['compiler_present']:
            state['waiting']={'at':datetime.now().isoformat(timespec='seconds'),**quiet}
            save(); continue
        run={'inserts':inserts,'start':datetime.now().isoformat(timespec='seconds'),'quiet_8s':quiet}
        a=processes(); t=time.perf_counter()
        path=ev/f"c7-idle-{inserts}-{len(state['attempts'])}.log"
        with path.open('w',encoding='utf-8') as log, subprocess.Popen([str(exe),'scenario_c7_chase','--ignored','--nocapture','--test-threads=1'],env=dict(os.environ,SCENARIO_C7_INSERTS=str(inserts)),stdout=log,stderr=log) as proc:
            watcher=psutil.Process(proc.pid); cpu0=0.; foreign=0.; builds_seen=set()
            while proc.poll() is None:
                try:
                    ct=watcher.cpu_times(); cpu0=ct.user+ct.system
                except psutil.NoSuchProcess: pass
                b=processes(); foreign+=build_seconds(a,b); builds_seen.update(n for n,_ in b.values() if n in heavy);a=b
                time.sleep(.15)
            elapsed=time.perf_counter()-t
            run.update({'elapsed_s':round(elapsed,3),'cpu_s_before_exit':round(cpu0,3),'core_percent_estimate':round(100*cpu0/elapsed,1),'compilers_during':sorted(builds_seen),'compiler_s':round(foreign,3),'returncode':proc.returncode,'log':str(path)})
        run['quiet_run']=not builds_seen and foreign<.12
        state['attempts'].append(run);save()
        if run['quiet_run']: break
state['done']=True;state.pop('waiting',None);save()
