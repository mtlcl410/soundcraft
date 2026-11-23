from pathlib import Path
import json, subprocess, time,sys
root=Path(__file__).resolve().parent
# Never compile while the measurement runner or its MIDI retries use this host.
import psutil
end=time.monotonic()+7200
def competing_runner():
    for proc in psutil.process_iter(['name','cmdline']):
        args=proc.info['cmdline'] or []
        if (proc.info['name'] or '').lower()=='python.exe' and any(Path(x).name in ('continue_rulers.py','retry_midi.py','environment.py') for x in args[1:3]):
            return True
    return False
while competing_runner():
    if time.monotonic()>end:raise TimeoutError('ruler still active')
    time.sleep(2)
for tree in ('mtc','follow'):
    with (root/f'audio/soundcraft-{tree}-build.log').open('wb') as log:
        subprocess.run([sys.executable,str(root/'audio/build_tools.py'),'soundcraft','--tree',str(root.parent/'g11-final-round'/tree)],stdout=log,stderr=subprocess.STDOUT,check=True)
