import json, pathlib, subprocess, sys, time
here=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent))
from desktop_sync import cmd
p=json.loads((here/'control.json').read_text())['port']
monitor=subprocess.Popen([sys.executable,'-u','main_return.py'],cwd=here,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
    line=monitor.stdout.readline()
    assert 'READY' in line,line
    for name,spp in [('queue20-a', 64), ('queue40-a', 64), ('queue60-a', 64), ('queue60-b', 64), ('queue40-b', 64), ('queue20-b', 64)]:
        assert not cmd(p,'transport.status')['playing']
        (here/'route-take.txt').write_text(name)
        time.sleep(.5)
        with subprocess.Popen([sys.executable,'-u','take_live.py',name],cwd=here,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True) as recording:
            line=recording.stdout.readline();print(line.strip(),flush=True)
            if 'READY' not in line:raise ValueError(line)
            if spp is not None:
                time.sleep(1.05)
                subprocess.run([sys.executable,'-u','exact_chorus.py',str(spp)],cwd=here,timeout=15,check=True)
            print(recording.communicate(timeout=22)[0],flush=True)
            assert recording.returncode==0
        (here/'route-take.txt').unlink()
        time.sleep(.35)
        subprocess.run([sys.executable,'assess.py',name],cwd=here,check=True,stdout=subprocess.DEVNULL)
        print(name,json.loads((here/(name+'-analysis.json')).read_text())['crash_count'],flush=True)
finally:
    (here/'route-take.txt').unlink(missing_ok=True)
    (here/'stop-monitor.flag').touch()
    print(monitor.communicate(timeout=10)[0],flush=True)
