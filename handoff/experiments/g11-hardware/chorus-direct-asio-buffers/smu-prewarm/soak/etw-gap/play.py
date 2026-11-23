"""Run the unchanged accompaniment after both witness streams and ETW are ready."""
from pathlib import Path
import sys,os,time
here=Path(__file__).resolve().parent
src=here.parent/'run.py'
text=src.read_text()
before="        with (case/(key+'.bin')).open('rb') as h: header=np.fromfile(h,'<u8',4)"
after="""        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            try:
                with (case/(key+'.bin')).open('rb') as h: header=np.fromfile(h,'<u8',4)
                if len(header)==4: break
            except FileNotFoundError: pass
            time.sleep(.05)
        else: raise RuntimeError('Missing ASIO witness header '+key)"""
assert text.count(before)==1
text=text.replace(before,after)
before="    a=anchor();mout.send_message([242,64,0]);time.sleep(.5)"
after="""    etw_dir=Path(os.environ['SC_ETW_DIR'])
    (etw_dir/('stream-'+tag+'.signal')).touch()
    deadline=time.monotonic()+180
    while not (etw_dir/('ready-'+tag+'.signal')).exists():
        if time.monotonic()>deadline: raise RuntimeError('Recorder readiness timeout')
        time.sleep(.1)
"""+before
assert text.count(before)==1
os.environ['SC_ETW_DIR']=str(here)
exec(compile(text.replace(before,after),str(src),'exec'),{'__name__':'__main__','__file__':str(src)})
