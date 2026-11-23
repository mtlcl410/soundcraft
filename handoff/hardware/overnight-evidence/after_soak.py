"""One bounded overnight queue. Preserve every failure, validate final local heads, close all devices."""
import json,os,subprocess,sys,time,traceback
from pathlib import Path
a=Path(__file__).resolve().parent;d=a.parent;r=d/'runs/home-20261123-002520-recorder'
status=a/'after-soak-status.json';results={}
def state(phase):
    tmp=status.with_suffix('.tmp');tmp.write_text(json.dumps(dict(phase=phase,timestamp=time.strftime('%Y-%m-%d %H:%M:%S %z'),results=results),indent=2));tmp.replace(status)
def run(name,cmd,cwd,env=None,timeout=1800):
    state(name)
    with (a/(name+'.log')).open('wb') as f:
        try:rc=subprocess.run(cmd,cwd=cwd,env=os.environ|(env or {}),stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except Exception as e:f.write(repr(e).encode());rc=-100
    results[name]=rc;state(name);return rc
def cargo(name,w,crate,opts,target,env=None):
    env={'CARGO_TARGET_DIR':str(target)}|(env or {})
    return run(name,[os.environ['COMSPEC'],'/d','/c',str(d.parent/'g11-a10-recovery/run.cmd'),'test','--offline','-j','4','-p',crate,'--lib',*opts],w,env)
def main():
    state('waiting_for_exclusive_hardware_window')
    limit=time.monotonic()+8000
    while time.monotonic()<limit:
        info=json.loads((a/'combined-two-hours-status.json').read_text())
        if info['phase'] in ('measured','incomplete'):break
        time.sleep(5)
    else:raise TimeoutError('Hardware recorder still running; no competing build started')
    long=a/'combined-two-hours'
    if (long/'result.json').is_file():
        run('h10-boundary-acceptance',[sys.executable,str(a/'test_combined_counts.py'),'-v'],a,{'SC_SOAK_CAPTURE':str(long)})
    # Isolate reference generator as well as relay, then rerun a short hardware control
    # before starting compilers. Native ASIO must have released the first stream.
    time.sleep(4)
    run('dedicated-source-control',[sys.executable,str(d/'environment.py'),'run','--panel',str(d/'panel.json'),'--out',str(a/'dedicated-source-control'),'--audio','--',sys.executable,str(a/'pilot3.py'),'96'],d,{'PYTHONPATH':os.pathsep.join(map(str,[d/'audio',d/'midi',d]))},240)
    if (a/'dedicated-source-control/result.json').is_file():
        run('source-control-analysis',[sys.executable,str(a/'summarize_soak.py'),str(a/'dedicated-source-control')],a)
    for name,folder in [('beat','overnight-beat-only'),('mtc','overnight-mtc-only'),('follow','overnight-g11')]:
        w=d/folder;head=subprocess.check_output(['git','-C',str(w),'rev-parse','HEAD'],text=True).strip();results[name+'_head']=head
        cargo('final-'+name+'-playback',w,'soundcraft-playback',['--','--test-threads=2'],d/'target-follow-confirm')
    # Verify the product selector on the two actual outlets. Keep this probe out of the PR patch.
    portdiag=d/'overnight-port-replay'
    subprocess.run(['git','-C',str(d/'overnight-beat-only'),'worktree','add','--detach',str(portdiag),results['beat_head']],check=True)
    ports=portdiag/'crates/playback/src/sync_output/ports.rs';ports_orig=ports.read_bytes()
    patched=ports_orig+b'\n#[cfg(test)] mod local_ports { use super::*; include!(r"'+str(a/'registry_physical.rs').encode()+b'"); }\n'
    ports.write_bytes(patched)
    try:
        cargo('product-physical-connectors',portdiag,'soundcraft-playback',['nightly_public_output_selector','--','--nocapture'],d/'target-follow-confirm')
    finally:
        if ports.read_bytes()==patched:ports.write_bytes(ports_orig)
    w=d/'overnight-g11'
    cargo('final-+-clock-scenarios',w,'soundcraft-ui-egui',['app::clock_follow','--','--include-ignored','--test-threads=1','--nocapture'],d.parent/'g11-follow-r3-target')
    # Use a separate, temporary diagnostic worktree with the *final* MTC-only branch.
    diag=d/'overnight-guide-wav-replay'
    subprocess.run(['git','-C',str(w),'worktree','add','--detach',str(diag),results['mtc_head']],check=True)
    p=diag/'crates/playback/src/mtc/tests.rs';old=p.read_bytes()
    mod=old+b'\nmod actual_guide { include!(r"'+str(a/'actual_guide_replay.rs').encode()+b'"); }\n';p.write_bytes(mod)
    mod+=b'\nmod nightly_winmm_probe { include!(r"'+str(a/'named_subport_probe.rs').encode()+b'"); }\n'
    p.write_bytes(mod)
    try:
        cargo('winmm-named-connector',diag,'soundcraft-playback',['nightly_winmm_probe','--','--nocapture'],d/'target-follow-confirm')
        for name,data in [('three-real-rolls',r/'paired-inputs.txt'),('six-fresh-din',a/'fresh-inputs.txt')]:
            cargo('actual-guide-'+name,diag,'soundcraft-playback',['actual_guide','--','--nocapture'],d/'target-follow-confirm',{'SC_GUIDE_PCM':str(a/'actual-guide-i16le.pcm'),'SC_FULL_TAKE_DATA':str(data)})
    finally:
        if p.read_bytes()==mod:p.write_bytes(old)
    with (a/'完測索引.zh-TW.md').open('w',encoding='utf-8') as f:
        print('# 夜間自動驗證結果\n',file=f)
        print('硬體完整計數若低於門檻，該列保留失敗。各實體測試的環境有效性另外記錄。\n',file=f)
        for name,rc in results.items():
            if name.endswith('_head'):print(f'- {name} `{rc}`',file=f);continue
            log=a/(name+'.log')
            summary=[l.strip() for l in log.read_text(encoding='utf-8-sig',errors='replace').splitlines() if l.startswith('test result:') or l.startswith('FAILED (')]
            print(f"- {name} {'通過' if rc==0 else '失敗'}（exit {rc}）。{' '.join(summary)} [紀錄]({name}.log)",file=f)
    state('finished')
try:main()
except BaseException:
    results['error']=traceback.format_exc();state('incomplete');raise

