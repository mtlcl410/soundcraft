from pathlib import Path
import sys,os
d=Path(__file__).resolve().parent.parent;p=d/'run_buffer.py'
os.environ['SC_PROF']=str(d/sys.argv[2]/'profile.bin')
s=p.read_text(encoding='utf-8-sig').replace("exe=here.parent/'soundcraft.exe'","exe=here.parent/'waveform-followup'/'soundcraft.exe'")
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
