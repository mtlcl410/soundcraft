from pathlib import Path
import sys, os, socket, json, time, subprocess, hashlib, shutil
ev=Path(__file__).resolve().parent
hw=ev.parent
sys.path.insert(0,str(hw))
from desktop_sync import cmd
src=hw/'smu-model12-chase.scraft'
song=ev/src.name
shutil.copy2(src,song)
exe=hw.parent/'r4-hardware-ee80920'/'soundcraft.exe'
cfg=ev/'preferences'
cfg.mkdir()
env=dict(os.environ,SOUNDCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(cfg),VST3_PATH='E:/S-MU2000-windows-x64/plugins',CLAP_PATH='E:/S-MU2000-windows-x64/plugins',S_MU2000_ROMS='E:/S-MU2000-windows-x64/roms')
with socket.socket() as sock:
 sock.bind(('127.0.0.1',0))
 port=sock.getsockname()[1]
si=subprocess.STARTUPINFO()
si.dwFlags|=subprocess.STARTF_USESHOWWINDOW
si.wShowWindow=0
with (ev/'desktop.log').open('wb') as log:
 proc=subprocess.Popen([str(exe),'--control',str(port),str(song)],cwd=ev,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,startupinfo=si)
control=dict(pid=proc.pid,port=port,exe=str(exe),sha256=hashlib.file_digest(exe.open('rb'),'sha256').hexdigest(),project_sha256=hashlib.file_digest(song.open('rb'),'sha256').hexdigest())
(ev/'control.json').write_text(json.dumps(control,indent=2))
for n in range(150):
 if proc.poll() is not None: raise RuntimeError('desktop exited')
 try: cmd(port,'transport.status'); break
 except OSError: time.sleep(.3)
else: raise RuntimeError('control timed out')
checks={}
for command,args in [('transport.status',{}),('setup.mtc',{}),('setup.mtc_output',{}),('ui.audio_device',{'list':True}),('setup.session',{})]:
 try: checks[command]=cmd(port,command,**args)
 except Exception as e: checks[command]=str(e)
(ev/'preflight.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
for k,v in checks.items(): print(k,str(v)[:400])
