from sequence import root,output,guarded
import time,sys,json,subprocess,winreg,psutil
deadline=time.monotonic()+7200
while any((p.info['name'] or '').lower()=='python.exe' and any(x.replace("\\","/").endswith(('/prepare_upper.py','/retry_midi.py','/continue_rulers.py')) for x in (p.info['cmdline'] or [])[1:3]) for p in psutil.process_iter(['name','cmdline'])):
    if time.monotonic()>deadline:raise TimeoutError('other runs still active')
    time.sleep(2)
k=r'Software\TASCAM\ModelMixer\ASIODRIVER'
with winreg.OpenKey(winreg.HKEY_CURRENT_USER,k,0,winreg.KEY_READ|winreg.KEY_SET_VALUE) as key:
    v,kind=winreg.QueryValueEx(key,'blockFrames')
    try:
        winreg.SetValueEx(key,'blockFrames',0,kind,512)
        for suffix in ('c','d','e'):
            ok=guarded(f'm1-independent-512-{suffix}',[sys.executable,root/'audio/m1.py',512,8,20],audio=True)
            if ok:break
    finally:winreg.SetValueEx(key,'blockFrames',0,kind,v)
subprocess.run([sys.executable,str(root/'report.py')],check=True)
