from pathlib import Path
import subprocess, sys,time
here=Path(__file__).resolve().parent
for name in ('tempo-a','tempo-b'):
    with (here/(name+'.log')).open('w') as log:
        subprocess.run([sys.executable,'-u',str(here/'take_live.py'),name],cwd=here,stdout=log,stderr=subprocess.STDOUT,check=True)
    time.sleep(.4)
