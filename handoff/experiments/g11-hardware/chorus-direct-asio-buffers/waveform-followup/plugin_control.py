from pathlib import Path
import sys,json,shutil,os
f=Path(__file__).resolve().parent;d=f.parent;session=d.parent/'chorus-direct-asio'/'session';alt=f/'no-vst-session';alt.mkdir(exist_ok=True)
song='Back to the Chorus.scraft';model=json.loads((session/song).read_bytes())
changed=[t for t in model['tracks'] if t['instrument']['plugin'].startswith('vst3:')];assert len(changed)==1
assert not changed[0]['instrument']['bypass'];changed[0]['instrument']=None
(alt/song).write_text(json.dumps(model),encoding='utf8');shutil.copytree(session/'Audio Files',alt/'Audio Files',dirs_exist_ok=True)
p=d/'run_buffer.py';s=p.read_text(encoding='utf-8-sig').replace("exe=here.parent/'soundcraft.exe'","exe=here.parent/'waveform-followup'/'soundcraft.exe'").replace("old=here.parent.parent/'chorus-direct-asio'/'session'","old=here.parent/'waveform-followup'/'no-vst-session'")
os.environ['SC_PROF']=str(d/sys.argv[2]/'profile.bin')
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})


