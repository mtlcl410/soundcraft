from pathlib import Path
import os,sys,time,subprocess
a=Path(__file__).resolve().parent;d=a.parent
sys.path.insert(0,str(d));os.environ.setdefault("SC_ACCEPTANCE_BUILD",str(d/'audio/build/f13949d9-build.json'))
# Only the harness changes. Preserve source, app, egress capture and analysis.
s=(a/'pilot.py').read_text().split('exec(compile')[0];exec(s)
src=src.replace("tx_name='Model 12 MIDI',rx_name='UM-ONE'","tx_name='Model 12 MIDI'").replace("tx_name=left,rx_name=right","rx_name=right")
i=src.index('        def pump():');j=src.index('        def log_port(',i)
src=src[:i]+'''        def pump():
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parent/'relay_process.py'),str(f),left])
            try:
                while not quit.wait(.05):
                    if proc.poll() is not None:raise RuntimeError(str(proc.returncode))
            except Exception as e:err.append(str(e));quit.set()
            finally:
                (f/'bridge-stop').touch()
                proc.wait(8)
'''+src[j:]
src=src.replace('origin=time.perf_counter_ns()+500_000_000','''for _ in range(100):
                if (f/'bridge-ready').exists(): break
                if err: raise RuntimeError(err)
                time.sleep(.1)
            else: raise RuntimeError('bridge not ready')
            origin=time.perf_counter_ns()+500_000_000''')
# Python capture queues on the source side are observable at the bridge, not in the parent.
src=src.replace('relay_q=physical.qsize()','relay_q=None').replace("max(x['relay_q'] for x in states)","None")
exec(compile(src,str(d/'soak_relay.py'),'exec'))

