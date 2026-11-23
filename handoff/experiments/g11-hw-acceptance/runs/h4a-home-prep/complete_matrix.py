"""Finish tonight's matrix, preserving failed attempts. Hardware is touched only when run as a script."""
import json,sys,subprocess,time
from pathlib import Path
here=Path(__file__).resolve().parent
root=here.parents[1]
sys.path.insert(0,str(root))
from home_din_summary import inspect
import psutil
def main():
    record=[]
    for rate in ('30','24','25','29.97df','29.97nd'):
        for side in ('forward','reverse'):
            def cases():
                return sorted((root/'runs').glob('home-*-din-'+rate+'-'+side))
            for attempt in range(3):
                prior=cases()
                finished=[(p,inspect(p)) for p in prior if (p/'result.json').is_file() and (p/'environment-result.json').is_file()]
                eligible=[r for _,r in finished if r['environment_valid'] and r['wire_equal']]
                # A valid negative result is just as final as a positive one.
                if eligible: break
                if len(prior)>=3:break
                while psutil.cpu_percent(interval=2)>45:time.sleep(3)
                with (here/'physical-resume.log').open('a',encoding='utf8') as log:
                    rc=subprocess.call([sys.executable,'-u','home_batch.py','din','--case',rate,side],cwd=root,stdout=log,stderr=subprocess.STDOUT)
                new=set(cases())-set(prior)
                if len(new)!=1:raise RuntimeError(f'No unique fresh result for {rate} {side}')
                p=new.pop()
                status=json.loads((p/'environment-result.json').read_text())
                record.append([p.name,rc,status]);(here/'attempts.json').write_text(json.dumps(record,indent=2))
                if any('remote' in s.lower() or 'Missing actual driver settings' in s for s in status['reasons']):
                    raise RuntimeError(status)
                print(p.name,status,flush=True)
if __name__=='__main__':main()

