"""One sequential hardware check, then synthesize a local terminal index when the queued work exits."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback
a=Path(__file__).resolve().parent
d=a.parent
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
def state(phase,**info):
    f=a/'night-index-status.json';tmp=f.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(phase=phase,updated=time.strftime('%Y-%m-%d %H:%M:%S %z'),**info),indent=2))
    tmp.replace(f)
def main():
    state('waiting_for_upstream_jobs')
    limit=time.monotonic()+10*3600
    while time.monotonic()<limit:
        if read(a/'final-night-status.json')['phase'] in ('incomplete','measured','complete_no_external_input_fault_to_repeat'):
            break
        time.sleep(10)
    else:raise TimeoutError('Previous work did not reach a terminal state; no competing I/O')
    # Only proceed once the other test's contexts have actually finished.
    dest=a/'physical-ext-transitions'
    if dest.exists():raise FileExistsError(dest)
    state('physical_ext_cycles')
    env=os.environ|{'SC_ACCEPTANCE_BUILD':str(d/'audio/build/f13949d9-build.json'),
                    'PYTHONPATH':os.pathsep.join(map(str,[d/'audio',d/'midi',d]))}
    with (a/'ext-cycles.log').open('xb') as f:
        rc=subprocess.run([sys.executable,'-X','utf8',str(d/'environment.py'),'run','--panel',str(d/'panel.json'),
                 '--out',str(dest),'--audio','--',sys.executable,'-X','utf8',str(a/'follow_lamp.py')],
                 cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=240).returncode
    with (a/'夜間收尾.zh-TW.md').open('w',encoding='utf-8') as f:
        print('# 夜間實機與產品回歸驗證\n', file=f)
        for folder in ('combined-two-hours','dedicated-source-control','dedicated-source-two-hours'):
            p=a/folder
            if not (p/'window-analysis.json').exists():
                print(f'- {folder} 尚無完整時窗。',file=f);continue
            s=read(p/'window-analysis.json')
            valid=read(p/'environment-result.json').get('environment_valid')
            print(f"- {folder}，{s['seconds']} 秒，環境有效 {valid}。Clock {s['clock']}/{s['expected_clock']}，QF {s['qf']}/{s['expected_qf']}，掉鎖 {s['observed_dropouts']} 次。[分析]({folder}/RESULT.zh-TW.md)",file=f)
        print('\n[三支本機分支與測試結束碼](after-soak-status.json) · [實機原始資料](physical-ext-transitions/)\n',file=f)
        result=read(dest/'result.json') if (dest/'result.json').is_file() else {}
        print(f"EXT 五輪狀態轉換，量測程序 exit {rc}。結果 `{result}`。",file=f)
    state('recorded',ext_exit=rc)
try:main()
except Exception:
    state('incomplete',reason=traceback.format_exc());raise
