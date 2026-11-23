from pathlib import Path
import json,subprocess,sys,time,psutil,winreg
from sequence import guarded,root,output
def wait_rulers():
    names=('retry_512.py','retry_midi.py','environment.py')
    while any((p.info['name'] or '').lower()=='python.exe' and any(Path(a).name in names for a in (p.info['cmdline'] or [])[1:3]) for p in psutil.process_iter(['name','cmdline'])):time.sleep(2)
if __name__=='__main__':
    wait_rulers()
    mode=sys.argv[1]
    sha=json.loads((root/'integrations.json').read_text())[mode][0]
    exe=root/f'audio/build/soundcraft-{sha[:8]}.exe'
    if not exe.exists():
        with (root/f'audio/integrated-{mode}-build.log').open('wb') as log:
            subprocess.run([sys.executable,str(root/'audio/build_tools.py'),'soundcraft','--tree',str(root/f'integrated-{mode}')],stdout=log,stderr=subprocess.STDOUT,check=True)
    print(exe,flush=True)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\TASCAM\ModelMixer\ASIODRIVER',0,winreg.KEY_READ|winreg.KEY_SET_VALUE) as key:
        saved,kind=winreg.QueryValueEx(key,'blockFrames')
        try:
            winreg.SetValueEx(key,'blockFrames',0,kind,256)
            name=f'm1-integration-{mode}-probe-01'
            ok=guarded(name,[sys.executable,root/'audio/m1_app.py',exe,256,1],audio=True)
            print('route probe valid',ok,flush=True)
        finally:winreg.SetValueEx(key,'blockFrames',0,kind,saved)
