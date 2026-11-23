"""Prepare the Model 12 comparisons. 'verify' is file-only; each other mode is started separately."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, time

ROOT=Path(__file__).resolve().parent
APP=ROOT/'audio/build/f13949d9-build.json'
RECOVERY=ROOT/'audio/build/eee6a79b-build.json'
def verify(path):
    meta=json.loads(path.read_text('utf-8-sig'))
    with open(meta['exe'],'rb') as f:
        assert hashlib.file_digest(f,'sha256').hexdigest()==meta['sha256'],path
    print(meta['head'],meta['sha256'],flush=True)
    return meta

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['verify','recorder','storage','din'])
    parser.add_argument('--case',nargs=2,metavar=('RATE','DIRECTION'))
    args=parser.parse_args()
    if args.case and (args.mode!='din' or args.case[0] not in ['30','24','25','29.97df','29.97nd'] or args.case[1] not in ['forward','reverse']):
        parser.error('Choose one supported DIN case')
    verify(APP);verify(RECOVERY)
    for fname in ['audio/manual-stimulus/chase-135s.wav','panel.json','panel-h4b.json','eject_storage_control.ps1','return_marker.py']:
        p = (ROOT/'runs/h4a-home-prep'/fname) if fname=='return_marker.py' else ROOT/fname
        assert p.is_file(),p
    if args.mode=='verify':return
    batch=time.strftime('%Y%m%d-%H%M%S')
    env=os.environ|{'SC_ACCEPTANCE_BUILD':str(APP)}
    def guarded(label,script,*params):
        out=ROOT/'runs'/f'home-{batch}-{label}'
        panel='panel-h4b.json' if label=='recorder' else 'panel.json'
        subprocess.run([sys.executable,'environment.py','run','--panel',panel,'--out',str(out),'--audio','--',sys.executable,script,*params],env=env,cwd=ROOT,check=True)
        return out
    if args.mode=='recorder':
        out=guarded('recorder','manual_run.py','manual')
        subprocess.run([sys.executable,'analyse_chase.py',str(out)],cwd=ROOT,check=True)
    if args.mode=='storage':
        # Storage intentionally changes the ASIO endpoint; its own per-window
        # rate, buffer, sequence and sample-position checks cover each epoch.
        out=ROOT/'runs'/f'home-{batch}-storage'
        out.mkdir()
        subprocess.run([sys.executable,'storage_idle_acceptance.py',str(out),str(RECOVERY)],cwd=ROOT,check=True)
        subprocess.run([sys.executable,'score_idle_tone.py',str(out)],cwd=ROOT,check=True)
        subprocess.run([sys.executable,'home_recovery_check.py',str(out)],cwd=ROOT,check=True)
    if args.mode=='din':
        for rate in ['30','24','25','29.97df','29.97nd']:
            for side in ['forward','reverse']:
                if args.case and [rate,side]!=args.case:continue
                out=guarded(f'din-{rate}-{side}','chase_ten.py',rate,side)
                from home_din_summary import inspect
                group=inspect(out)
                (out/'wire-and-timing-check.json').write_text(json.dumps(group,indent=2))
                with (out/'return-marker-check.json').open('x') as f:
                    subprocess.run([sys.executable,'runs/h4a-home-prep/return_marker.py',str(out)],cwd=ROOT,check=True,stdout=f)
if __name__=='__main__':main()

