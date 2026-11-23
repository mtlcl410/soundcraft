import contextlib, hashlib, json, os, pathlib, shutil, socket, subprocess, sys, time
here=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent))
from desktop_sync import cmd
old=here
song=old/'Back to the Chorus.scraft'
exe=here.parent.parent/'g11-follow-r3-target'/'debug'/'soundcraft.exe'
env=dict(os.environ,SOUNDCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(here/'private-settings'),VST3_PATH='E:/S-MU2000-windows-x64/plugins',CLAP_PATH='E:/S-MU2000-windows-x64/plugins',S_MU2000_ROMS='E:/S-MU2000-windows-x64/roms')
(here/'private-settings').mkdir(exist_ok=True)
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
with (here/'desktop.log').open('wb') as log:
    proc=subprocess.Popen([str(exe),'--control',str(port),str(song)],cwd=old,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,startupinfo=si)
(here/'control.json').write_text(json.dumps(dict(port=port,pid=proc.pid,sha256=hashlib.file_digest(exe.open('rb'),'sha256').hexdigest(),project_sha256=hashlib.file_digest(song.open('rb'),'sha256').hexdigest())))
for n in range(180):
    if proc.poll() is not None:raise RuntimeError((here/'desktop.log').read_text())
    try:cmd(port,'transport.status');break
    except OSError:time.sleep(.25)
devices=cmd(port,'ui.audio_device',list=True)['systems']
out=next(d['name'] for api in devices for d in api['outputs'] if 'S/PDIF' in d['name'])
print(cmd(port,'ui.audio_device',output=out,sample_rate=48000,buffer_size=480),flush=True)
print(cmd(port,'setup.midi_clock_follow',input='UM-ONE',enabled=True,loss_policy='coast'),flush=True)

