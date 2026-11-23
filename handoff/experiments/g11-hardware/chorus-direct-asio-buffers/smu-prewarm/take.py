from pathlib import Path
import os,sys
w=Path(__file__).resolve().parent; d=w.parent; case=d/sys.argv[2];lib=Path(sys.argv[3]).resolve()
p=d/'run_buffer.py'
os.environ['SC_PROF']=str(case/'profile.bin')
os.environ['SMU_WARM_TRACE']=str(case/'cold.txt')
s=p.read_text(encoding='utf-8-sig').replace("exe=here.parent/'soundcraft.exe'", "exe=here.parent/'waveform-followup'/'soundcraft.exe'")
s=s.replace("if name=='launch.py':","if name=='launch.py':\n    s=s.replace('E:/S-MU2000-windows-x64/plugins',"+repr(lib.as_posix())+")")
# Verify the loaded DLL in the specific SoundCraft process before sending MIDI.
s=s.replace(' snap={}', """ pid=json.loads((case/'control.json').read_bytes())['pid']
 ps=f"(Get-Process -Id {pid}).Modules | Where-Object ModuleName -like '*MU2000*' | Select-Object -ExpandProperty FileName"
 modules=subprocess.check_output(['powershell','-NoProfile','-Command',ps],text=True).strip().splitlines()
 assert len(modules)==1 and Path(modules[0]).resolve().is_relative_to(Path(EXPECTED_LIB)),modules
 (case/'loaded-plugin.json').write_text(json.dumps(dict(path=modules[0],sha256=hashlib.file_digest(open(modules[0],'rb'),'sha256').hexdigest())))
 snap={}""".replace('EXPECTED_LIB',repr(str(lib))))
if '--short' in sys.argv: s=s.replace("('late-a',65),('exact-b',64),('exact-c',64),('late-b',65),('exact-d',64)", "('late-a',65)")
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
