"""Sequential no-panel hardware confirmation; raw warnings and failed counts remain local."""
import json,os,subprocess,sys,time,traceback
from pathlib import Path
from statistics import median
from cue_hardware import run as short_run

a=Path(__file__).resolve().parent;d=a.parent;rev='4cfaf099'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def update(label,**values):
    tmp=a/'reboot-0823-progress.tmp'
    tmp.write_text(json.dumps(dict(phase=label,updated=time.strftime('%Y-%m-%d %H:%M:%S %z'),**values),indent=2))
    tmp.replace(a/'reboot-0823-progress.json')
def command(name,cmd,cwd,env,timeout):
    with (a/(name+'.log')).open('xb') as f:
        return subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
def main():
    env=os.environ|{'SC_ACCEPTANCE_BUILD':str(d/'audio/build'/f'{rev}-build.json'),'PYTHONPATH':os.pathsep.join(map(str,[d/'audio',d/'midi',d]))}
    update('waiting_for_binary_and_software_checks')
    for _ in range(1800):
        if Path(env['SC_ACCEPTANCE_BUILD']).exists() and (a/'morning-software-finished.json').exists():break
        time.sleep(2)
    else:raise RuntimeError('Build or checks timed out')
    software=read(a/'morning-software-finished.json')
    if not all(v==0 for v in software.values()):raise RuntimeError(f'Check failed: {software}')
    p=a/'reboot-0823-two-hours'
    update('two_hour_hardware',seconds=7200,binary=rev)
    code=command('reboot-0823-two-hours',[sys.executable,'-X','utf8',str(d/'environment.py'),'run','--panel',str(d/'panel.json'),
            '--out',str(p),'--audio','--',sys.executable,'-X','utf8',str(a/'pilot3.py'),'7200'],d,env,7600)
    if not (p/'result.json').exists():raise RuntimeError(f'raw hardware result missing: {code}')
    for script in ['summarize_soak','resource_windows','soak_clock_domains','counter_holdout','asio_header_stats']:
        rc=command('reboot-0823-'+script,[sys.executable,str(a/(script+'.py')),str(p)],a,env,300)
        if rc:raise RuntimeError(f'{script} failed: {rc}')
    result=read(p/'result.json');measure=read(p/'counter-domains.json')
    strict=command('reboot-0823-counts',[sys.executable,str(a/'test_combined_counts.py'),'-v'],a,env|{'SC_SOAK_CAPTURE':str(p)},50)
    states=[json.loads(l) for l in (p/'state.jsonl').read_text().splitlines()]
    phase=[r['s']['clock_follow']['phase_error_us'] for r in states if r['s']['clock_follow']['state']=='Locked' and r['s']['clock_follow']['phase_error_us'] is not None]
    early=median(phase[:600])/1000; late=median(phase[-600:])/1000
    (p/'複測摘要.zh-TW.md').write_text(f"""# 本機候選版 H-10 複測

48 kHz／256 實體 DIN 兩小時。環境有效 {read(p/'environment-result.json')['environment_valid']}。原始 Clock {result['received_clock']}/{result['expected_clock']}，QF {result['received_qf']}/{result['expected_qf']}，失鎖 {result['dropout_count']} 次。

排除啟停的十一個完整十分鐘視窗，實測音訊裝置時鐘 {measure['median_device_ppm']:+.3f} ppm。外送 Clock 比輸入多 {measure['observed_extra_f8']:+d} 個，QF 超額 {measure['observed_extra_qf']:+.0f} 個。跟隨端相位誤差首末約十分鐘的中位數 {early:+.3f}、{late:+.3f} ms。原始嚴格計數測試 exit {strict}。

[詳細分窗](counter-domains.json) · [起停、記憶體與佇列](RESULT.zh-TW.md)
""",encoding='utf-8')
    update('measured',environment_exit=code,strict_counts_exit=strict,clock=result['received_clock'],qf=result['received_qf'],dropouts=result['dropout_count'],first_phase_ms=early,last_phase_ms=late,interior_extra_clock=measure['observed_extra_f8'],interior_extra_qf=measure['observed_extra_qf'])
try:main()
except BaseException:
    update('incomplete',error=traceback.format_exc());raise
