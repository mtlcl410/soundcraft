"""Exclusive hardware queue. Save the original driver preferences and restore them on all exits."""
import json,sys,time,subprocess,winreg
from sequence import root,output

def read(p):return json.loads(p.read_text())
def run_case(kind,side,rate,n,duration,offset):
    for attempt in range(1,4):
        name=f'h1h2-{kind}-{side}-{rate}-{n}-{duration}-r{attempt}'
        d=output/name
        if not d.exists():
            with (root/f'{name}.log').open('wb') as log:
                rc=subprocess.run([sys.executable,root/'environment.py','run','--panel',root/'panel.json','--out',d,'--audio','--',sys.executable,
                    root/'output_clock.py',side,str(rate),str(n),str(duration),str(offset),'map' if kind=='map' else 'steady'],cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
        if (d/'environment-result.json').exists():
            env=read(d/'environment-result.json')
            if env['environment_valid'] and (d/'result.json').exists():
                result=read(d/'result.json')
                print(name,result,flush=True)
                return result
            if env['command_exit'] not in (0,None):
                print(name,env,flush=True)
                return {}
    return {}

def main():
    deadline=time.monotonic()+1800
    while not (output/'h4a-integration-29.97nd-reverse-01/environment-result.json').is_file():
        if time.monotonic()>deadline:raise TimeoutError('MTC suite has not released ASIO')
        time.sleep(1)
    subprocess.run([sys.executable,root/'report.py'],check=True)
    # Compile and run the offline #1663 proof in the gap between device owners.
    with (root/'software-replay-launch.log').open('wb') as log:
        subprocess.run([sys.executable,root/'software_replay.py'],cwd=root,stdout=log,stderr=subprocess.STDOUT)
    time.sleep(4)
    keyname=r'Software\TASCAM\ModelMixer\ASIODRIVER'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,keyname,0,winreg.KEY_READ|winreg.KEY_SET_VALUE) as k:
        saved={p:winreg.QueryValueEx(k,p) for p in ('blockFrames','sampleRate')}
        def setpanel(n,rate):
            for prop,value in [('blockFrames',n),('sampleRate',rate)]:
                winreg.SetValueEx(k,prop,0,saved[prop][1],value)
        try:
            for side in ('reverse','forward'):
                setpanel(256,48000)
                run_case('map',side,48000,256,12,0)
            calibrated={}
            for side in ('reverse','forward'):
                res=run_case('cal',side,48000,256,60,0)
                if res.get('complete_sequence_alignment_verified'):calibrated[side]=res['calibration_recommended_samples']
            for side in ('reverse','forward'):
                run_case('steady',side,48000,256,600,0)
            for rate in (48000,44100):
                for n in (128,512):
                    setpanel(n,rate)
                    for side,offset in calibrated.items():
                        # Port calibration is persisted in samples by SoundCraft.
                        run_case('calibrated',side,rate,n,600,offset)
        finally:
            for p,(v,t) in saved.items():winreg.SetValueEx(k,p,0,t,v)
            (output/'clock-output-panel-restored.json').write_text(json.dumps({p:winreg.QueryValueEx(k,p)[0] for p in saved}))
            subprocess.run([sys.executable,root/'report.py'],check=True)
if __name__=='__main__':main()

