"""Twenty separate output/input opens per size, always restore the vendor panel."""
import json,sys,time,winreg
from sequence import root,output,guarded
def main(label):
    head=json.loads((root/'integrations.json').read_text())['follow'][0]
    exe=root/f'audio/build/soundcraft-{head[:8]}.exe'
    results={}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\TASCAM\ModelMixer\ASIODRIVER',0,winreg.KEY_READ|winreg.KEY_SET_VALUE) as key:
        saved,kind=winreg.QueryValueEx(key,'blockFrames')
        try:
            for n in (128,256,512):
                name=f'm1-integration-{n}-{label}'
                if (output/name).exists():raise FileExistsError(name)
                winreg.SetValueEx(key,'blockFrames',0,kind,n)
                results[n]=guarded(name,[sys.executable,root/'audio/m1_app.py',exe,n,20],audio=True)
                print(n,results[n],flush=True)
        finally:winreg.SetValueEx(key,'blockFrames',0,kind,saved)
    return int(not all(results.values()))
if __name__=='__main__':sys.exit(main(sys.argv[1]))

