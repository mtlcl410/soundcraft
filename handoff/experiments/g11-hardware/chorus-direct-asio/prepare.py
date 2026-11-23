import json, pathlib, shutil, os, hashlib
d=pathlib.Path(__file__).resolve().parent
source=d.parent/'chorus-rehearsal-1795189811276'
old=d.parent/'chorus-main-return-split'
for name in ['assess.py','exact_chorus.py','Crash.wav']:shutil.copyfile(old/name,d/name)
song=source/'Back to the Chorus.scraft'
j=json.loads(song.read_bytes());assert j['outputs']==[dict(name='Out 1-2',first_channel=0,format='Stereo')]
sessions=d/'session';sessions.mkdir(exist_ok=True);shutil.copytree(source/'Audio Files',sessions/'Audio Files',dirs_exist_ok=True)
# Open a byte-identical private copy. Route the main bus in memory using setup.io.
shutil.copyfile(song,sessions/song.name)
p=(old/'launch.py').read_text();p=p.replace("old=here.parent/'chorus-rehearsal-1795189811276'","old=here/'session'"); p=p[:p.index("devices=cmd")]+"""routing=cmd(port,'setup.io',action='set_output',name='Out 1-2',first_channel=8)
print(routing,flush=True)
setup=cmd(port,'ui.audio_device',system='ASIO',output='Model Mixer ASIO',input='Model Mixer ASIO',sample_rate=44100,buffer_size=256)
print(setup,flush=True)
dev=setup['device'];assert dev['name']=='Model Mixer ASIO' and dev['channels']==10 and dev['sample_rate']==44100 and not dev['silent'],setup
print(cmd(port,'setup.midi_clock_follow',input='UM-ONE',enabled=True,loss_policy='coast'),flush=True)
(here/'route.json').write_text(json.dumps(dict(routing=routing,audio=setup),indent=2))
""";(d/'launch.py').write_text(p)

