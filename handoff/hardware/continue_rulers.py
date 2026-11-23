"""Run the remaining rulers serially after compilation. Restore the TASCAM panel buffer."""
import json, subprocess, sys, time, winreg
from pathlib import Path
from sequence import root, output, guarded
exe=root/'audio/build/soundcraft-8fd15068.exe'
def run():
    deadline=time.monotonic()+5400
    while not exe.exists():
        if time.monotonic()>deadline:raise TimeoutError('instrumented build')
        log=root/'audio/soundcraft-beat-build.log'
        if log.exists() and 'CalledProcessError:' in log.read_text(errors='ignore'):break
        time.sleep(3)
    keypath=r'Software\TASCAM\ModelMixer\ASIODRIVER'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,keypath,0,winreg.KEY_READ|winreg.KEY_SET_VALUE) as key:
        saved,kind=winreg.QueryValueEx(key,'blockFrames')
        state={'saved_preference':saved,'registry':keypath}
        (root/'runs/panel-buffer-before.json').write_text(json.dumps(state))
        try:
            winreg.SetValueEx(key,'blockFrames',0,kind,512)
            ok=guarded('m1-independent-512-b',[sys.executable,root/'audio/m1.py',512,8,20],audio=True)
            print('512 independent',ok,flush=True)
            name='m2-forward-b'
            ok=guarded(name,[sys.executable,root/'midi/midi_path.py','run','--tx','UM-ONE','--rx','Model 12 MIDI','--out',output/name/'data'])
            print('MIDI forward',ok,flush=True)
            if exe.is_file():
                for n in (128,256,512):
                    winreg.SetValueEx(key,'blockFrames',0,kind,n)
                    ok=guarded(f'm1-soundcraft-{n}-a',[sys.executable,root/'audio/m1_app.py',exe,n,20],audio=True)
                    print('SoundCraft',n,ok,flush=True)
        finally:
            winreg.SetValueEx(key,'blockFrames',0,kind,saved)
            (root/'panel-buffer-restored.json').write_text(json.dumps({'blockFrames':winreg.QueryValueEx(key,'blockFrames')[0]}))
            subprocess.run([sys.executable,str(root/'report.py')],check=True)
if __name__=='__main__':run()
