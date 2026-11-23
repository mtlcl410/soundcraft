"""Run the 7200 s comparison on the same setup after a qualified phase matrix."""
from pathlib import Path
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime

here=Path(__file__).parent.resolve()
root=here.parent
sha=sys.argv[1]
matrix=json.loads((here/f'stop-ordinal-matrix-{sha}.json').read_text())
assert len(matrix)==8 and all(r['valid'] and r['omitted']==0 for r in matrix)
assert any(r['suppressions'] for r in matrix)
label=f'stop-ordinal-{sha}-two-hours'
folder=here/label
env=os.environ|dict(SC_ACCEPTANCE_BUILD=str(root/'audio/build'/f'{sha}-build.json'),
    SC_AUDIT_BEAT_COMPENSATION='on', SC_AUDIT_STOP_ADVANCE_MS='0',
    PYTHONPATH=os.pathsep.join(map(str,[root/'audio',root/'midi',root])))
def run(log,args,timeout):
    with (here/log).open('xb') as f:
        return subprocess.run([sys.executable,'-X','utf8',*map(str,args)],cwd=root,env=env,
                timeout=timeout,stdout=f,stderr=subprocess.STDOUT).returncode

started=datetime.now().astimezone().isoformat(timespec='seconds')
rc=run(label+'.log',[root/'environment.py','run','--panel',root/'panel.json','--out',folder,'--audio',
        '--',sys.executable,'-X','utf8',here/'pilot3.py',7200],7670)
if not (folder/'result.json').is_file():
    raise RuntimeError(f'No hardware capture, exit {rc}')
for script in ['asio_header_stats','soak_clock_domains']:
    if run(label+'-'+script+'.log',[here/(script+'.py'),folder],400):
        raise RuntimeError(script)
env['SC_SOAK_CAPTURE']=str(folder)
strict=run(label+'-strict.log',[here/'test_combined_counts.py','-v'],60)
def read(file):
    return json.loads((folder/file).read_text(encoding='utf-8-sig'))
result=read('result.json')
env_status=read('environment-result.json')
stages=(folder/'application.log').read_text(errors='replace')
filtered=re.findall(r'SC_STOP_CUTOFF (\d+) (\d+) (\d+) (\d+)',stages)
stamps=[list(map(int,x)) for x in re.findall(r'SC_STOP_QPC (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',stages) if int(x[0])>0]
with (folder/'egress.csv').open() as f:
    stopped=False
    late=0
    for row in csv.DictReader(f):
        if row['hex']=='fc': stopped=True
        elif row['hex']=='f8' and stopped: late+=1
summary=dict(started=started,completed=datetime.now().astimezone().isoformat(timespec='seconds'),
    valid=env_status,strict_exit=strict,source=result['source'],physical_input=result['physical_input'],captured_input=result['relayed_input'],
    output=result['received_clock'],qf=result['received_qf'],dropouts=result['dropout_count'],qf_piece_discontinuities=result['discontinuous_qf_pieces'],
    sends_after_output_stop=late,native_stops=stamps,suppressions=filtered,asio=read('asio-callback-histogram.json'))
(folder/'stop-verdict.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)

