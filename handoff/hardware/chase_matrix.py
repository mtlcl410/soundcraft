"""Run the ten-take generator scenarios after the ASIO ruler releases the device."""
import json,subprocess,sys,time
from pathlib import Path
from sequence import root,output,guarded
if __name__=='__main__':
    until=time.monotonic()+900
    while not (output/'m1-integration-512-formal-01/environment-result.json').exists():
        if time.monotonic()>until:raise TimeoutError('waiting for audio ruler')
        time.sleep(.5)
    time.sleep(2)
    for rate in ('30','24','25','29.97df','29.97nd'):
        for side in ('forward','reverse'):
            name=f'h4a-integration-{rate}-{side}-01'
            if (output/name).exists():raise FileExistsError(name)
            with (root/f'{name}.log').open('wb') as log:
                cmd=[sys.executable,root/'environment.py','run','--panel',root/'panel.json','--out',output/name,'--audio','--',sys.executable,root/'chase_ten.py',rate,side]
                rc=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
            print(name,rc,flush=True)
            if rc and not (output/name/'result.json').exists():
                raise RuntimeError(f'{name} did not yield a full measurement')

