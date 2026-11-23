import json
import os
import re
import statistics
import subprocess
from pathlib import Path
import psutil

a = Path(__file__).resolve().parent
d = a.parent
executables = {}
for name, target in [('before', 'g11-follow-target'), ('after', 'g11-verify-beat-target')]:
    tree = d / ('morning-poll-bench-'+name)
    module = tree / 'crates/playback/src/midi.rs'
    if 'acceptance_poll_cost_one_process' not in module.read_text():
        with module.open('a') as f:
            f.write((a/'host_poll_cost.rs').read_text())
    env = os.environ | {'CARGO_TARGET_DIR':str(d.parent/target)}
    args = [os.environ['COMSPEC'], '/d','/c',str(d.parent/'g11-a10-recovery/run.cmd'), 'test','--offline','-p','soundcraft-playback','--lib','--no-run','--message-format=json']
    proc = subprocess.run(args, env=env, cwd=tree, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace')
    (a/f'host-poll-cost-{name}-build.log').write_text(proc.stdout, encoding='utf-8')
    proc.check_returncode()
    artifacts = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith('{')]
    executables[name], = [r['executable'] for r in artifacts if r.get('executable') and r['target']['name']=='soundcraft_playback']

p=psutil.Process()
core=p.cpu_affinity()[-1]
p.cpu_affinity([core])
measurements={'before':[],'after':[]}
for name in ('before','after','after','before')*4:
    output=subprocess.check_output([executables[name],'acceptance_poll_cost_one_process','--ignored','--nocapture','--test-threads=1'],text=True,errors='replace')
    if '1 passed' not in output:
        raise RuntimeError(output)
    measurements[name].append(float(re.search(r'SC_POLL_NS ([0-9.]+)',output)[1]))
median={k:statistics.median(v) for k,v in measurements.items()}
result=dict(method='single logical CPU, warmed 500,000 polls, second 500,000 timed; ABBA four times',logical_cpu=core,
            ns_per_poll=measurements,median_ns=median,relative_saving_percent=100*(1-median['after']/median['before']))
(a/'host-poll-abba.json').write_text(json.dumps(result,indent=2))
print(result,flush=True)
