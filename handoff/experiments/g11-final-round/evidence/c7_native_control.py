"""Take C-7 controls at strict idle when available and at measured desktop load otherwise."""
from pathlib import Path
from datetime import datetime
from collections import Counter
import ctypes, ctypes.wintypes as w, os, psutil, subprocess, time, json
ev=Path(__file__).resolve().parent
strict_path=ev/'c7-idle-comparison.json'; desk_path=ev/'c7-desktop-comparison.json'
strict=json.loads(strict_path.read_text('utf8'))
if strict.get('done'):raise SystemExit
# Replace only the dedicated C-7 gate originally launched by this lane. Never interrupt an active benchmark.
for p in psutil.process_iter(['pid','name','cmdline']):
    a=p.info['cmdline'] or []
    if p.info['name'].lower()=='python.exe' and any(arg.replace('\\','/').endswith('/c7_idle_reference.py') for arg in a):
        p.suspend()
        if any(q.is_running() for q in p.children()):
            p.resume();raise SystemExit('strict benchmark active; keep the current supervisor')
        p.terminate(); p.wait(timeout=10)
desk={k:v for k,v in strict.items() if k in ['binary','sha256','logical_cpus']};desk['attempts']=[]
if desk_path.exists():
    previous=json.loads(desk_path.read_text('utf8'))
    if all('native-' in r['log'] for r in previous['attempts']):desk=previous
def save(p,d):
    t=p.with_suffix('.json.tmp'); t.write_text(json.dumps(d,indent=2),encoding='utf8');t.replace(p)
def now():return datetime.now().isoformat(timespec='seconds')
from nt_process_times import proc_times
dev={'rustc.exe','cargo.exe','cargo-clippy.exe','clippy-driver.exe','link.exe','lld-link.exe','cl.exe','rust-lld.exe','clang.exe','clang-cl.exe','rustfmt.exe','pytest.exe'}
def is_dev(n):
    return n in dev or n.startswith(('soundcraft_','cargo-test','cargo-nextest','load-bench')) or n=='soundcraft.exe'
def observation(sec,except_pid=None):
    start=now();before=proc_times(); observed=set()
    psutil.cpu_percent()
    finish=time.perf_counter()+sec
    while time.perf_counter()<finish:
        cur=proc_times()
        observed.update(n for pid,(n,_) in cur.items() if pid!=except_pid and is_dev(n))
        time.sleep(min(.5,max(0,finish-time.perf_counter())))
    end=proc_times(); core=Counter()
    for k,(n,v) in end.items():
        if n not in {'system idle process','idle'} and k!=except_pid:
            core[n]+=max(0,v-before.get(k,(n,0))[1])
    return dict(start=start,end=now(),system_percent=psutil.cpu_percent(),compiler_seconds=round(sum(s for n,s in core.items() if is_dev(n)),3),
                compiler_present=sorted(observed),top_one_core_percent={n:round(100*s/sec,1) for n,s in core.most_common(6)})
def exact_cpu(handle):
    creation=w.FILETIME();term=w.FILETIME();kernel=w.FILETIME();user=w.FILETIME()
    if not ctypes.windll.kernel32.GetProcessTimes(w.HANDLE(handle),ctypes.byref(creation),ctypes.byref(term),ctypes.byref(kernel),ctypes.byref(user)): return 0
    return sum((t.dwHighDateTime<<32)+t.dwLowDateTime for t in [kernel,user])/1e7
def completed(state):
    return {r['inserts'] for r in state['attempts'] if r['quiet_run']}
while True:
    pre=observation(8.)
    strict_run=not pre['compiler_present'] and pre['system_percent']<=12.5
    if pre['compiler_present'] or not strict_run and len(completed(desk))==3:
        strict['waiting']={'at':now(),**pre};save(strict_path,strict);continue
    state,path,label=(strict,strict_path,'idle') if strict_run else (desk,desk_path,'desktop')
    idx=next((i for i in (0,2,6) if i not in completed(state)),None)
    if idx is None:break
    start=now(); begin=time.perf_counter(); logfile=ev/f'c7-{label}-native-{idx}-{len(state["attempts"])}.log'
    competitors=set(); host=[]; times=proc_times()
    with logfile.open('w') as log,subprocess.Popen([strict['binary'],'scenario_c7_chase','--ignored','--nocapture','--test-threads=1'],env=os.environ|{'SCENARIO_C7_INSERTS':str(idx)},stdout=log,stderr=log) as proc:
        psutil.cpu_percent()
        while proc.poll() is None:
            competitors.update(n for pid,(n,_) in proc_times().items() if pid!=proc.pid and is_dev(n))
            time.sleep(.15)
        host_load=psutil.cpu_percent();elapsed=time.perf_counter()-begin;cpu=exact_cpu(proc._handle);rc=proc.returncode
    post=observation(8.)
    r=dict(inserts=idx,start=start,quiet_8s=pre,after_8s=post,elapsed_s=round(elapsed,3),cpu_s=round(cpu,4),core_percent=round(100*cpu/elapsed,1),
           compilers_during=sorted(competitors),system_during_percent=host_load,returncode=rc,log=str(logfile),quiet_run=not competitors and not post['compiler_present'] and rc==0)
    state['attempts'].append(r);state['done']=len(completed(state))==3;state.pop('waiting',None);save(path,state)
    if state is strict and state['done']:break
