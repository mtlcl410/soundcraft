"""Finalize the local audit, including a bounded repeat when the reference itself stalled."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

a = Path(__file__).resolve().parent
d = a.parent
out = a / 'dedicated-source-two-hours'
status = a / 'final-night-status.json'

def data(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def save(phase, **extra):
    tmp = status.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(phase=phase,updated=time.strftime('%Y-%m-%d %H:%M:%S %z'),**extra),
                              ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(status)

def run():
    save('waiting_for_isolated_control_and_software_tests')
    until = time.monotonic() + 6*3600
    while time.monotonic() < until:
        s=data(a/'after-soak-status.json')
        if s['phase'] in ('finished','incomplete'):
            break
        time.sleep(5)
    else:
        raise TimeoutError('Earlier validation queue has not completed. Hardware retest withheld.')
    original = a/'combined-two-hours/window-analysis.json'
    control=a/'dedicated-source-control'
    if not original.is_file() or not (control/'window-analysis.json').is_file():
        save('incomplete',reason='Missing diagnostics for original or 96-second control')
        return
    first = data(original)
    short = data(control/'window-analysis.json')
    short_result = data(control/'result.json')
    inputs = ['sender','din','software_ingress']
    if not any(first['physical_gap_distributions'][k]['over_150ms'] for k in inputs):
        save('complete_no_external_input_fault_to_repeat')
        return
    if (not data(control/'environment-result.json').get('environment_valid')
        or short_result['source']!=short_result['physical_input']
        or short_result['source']!=short_result['relayed_input']
        or any(short['physical_gap_distributions'][k]['over_150ms'] for k in inputs)):
        save('incomplete',reason='96-second control still has an environment or external input fault; no second two-hour run')
        return
    if out.exists():
        raise FileExistsError(out)
    save('running_isolated_reference_two_hours',planned_seconds=7200)
    env=os.environ|{'PYTHONPATH':os.pathsep.join(map(str,[d/'audio', d/'midi',d]))}
    with (a/'dedicated-source-two-hours.log').open('xb') as f:
        rc=subprocess.run([sys.executable,'-X','utf8',str(d/'environment.py'),'run','--panel',str(d/'panel.json'),
                  '--out',str(out),'--audio','--',sys.executable,'-X','utf8',str(a/'pilot3.py'),'7200'],
                  cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=7600).returncode
    if not (out/'result.json').is_file():
        raise RuntimeError(f'Isolated acquisition did not save data (exit {rc})')
    subprocess.run([sys.executable,'-X','utf8',str(a/'summarize_soak.py'),str(out)],check=True,cwd=d)
    summary=data(out/'window-analysis.json')
    with (a/'dedicated-source-counts.log').open('wb') as f:
        counts_rc=subprocess.run([sys.executable,str(a/'test_combined_counts.py'),'-v'],cwd=a,
               env=env|{'SC_SOAK_CAPTURE':str(out)},stdout=f,stderr=subprocess.STDOUT).returncode
    save('measured',environment_valid=data(out/'environment-result.json').get('environment_valid'),
         recorder_exit=rc,counts_test_exit=counts_rc,dropouts=summary['observed_dropouts'],
         clock=summary['clock'],expected_clock=summary['expected_clock'],qf=summary['qf'],expected_qf=summary['expected_qf'],
         report=str(out/'RESULT.zh-TW.md'))

try:
    run()
except Exception:
    save('incomplete',error=traceback.format_exc())
    raise
