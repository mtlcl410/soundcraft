import contextlib, hashlib, json, os, pathlib, shutil, socket, subprocess, sys, time
here=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent.parent))
from desktop_sync import cmd
old=here.parent.parent/'chorus-direct-asio'/'session'
song=old/'Back to the Chorus.scraft'
exe=here.parent/'waveform-followup'/'soundcraft.exe'
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
routing=cmd(port,'setup.io',action='set_output',name='Out 1-2',first_channel=8)
print(routing,flush=True)
setup=cmd(port,'ui.audio_device',system='ASIO',output='Model Mixer ASIO',input='Model Mixer ASIO',sample_rate=44100,buffer_size=128)
print(setup,flush=True)
dev=setup['device'];assert dev['name']=='Model Mixer ASIO' and dev['channels']==10 and dev['sample_rate']==44100 and not dev['silent'],setup
print(cmd(port,'setup.midi_clock_follow',input='UM-ONE',enabled=True,loss_policy='coast'),flush=True)
(here/'route.json').write_text(json.dumps(dict(routing=routing,audio=setup),indent=2))
