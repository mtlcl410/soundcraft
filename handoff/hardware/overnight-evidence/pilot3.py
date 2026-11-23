"""Run the isolated source and relay with the original SoundCraft capture paths."""
from pathlib import Path
import os,sys,subprocess,time
a=Path(__file__).resolve().parent;d=a.parent
s=(a/'pilot2.py').read_text().rsplit("exec(compile",1)[0];exec(s)
src=src.replace("tx,physical,_=stack.enter_context(live_midi(tx_name='Model 12 MIDI'))","tx=None")
start=src.index('            origin=time.perf_counter_ns()');end=src.index('            for thread in threads:thread.join(9)',start)
src=src[:start]+"""            sourceproc=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parent/'source_process.py'),str(f),str(secs)])
            while sourceproc.poll() is None:
                if err:
                    sourceproc.terminate();raise RuntimeError(err)
                time.sleep(.2)
            if sourceproc.returncode: raise RuntimeError(f'source exited {sourceproc.returncode}')
        finally:
            time.sleep(.6);quit.set()
"""+src[end:]
exec(compile(src,str(d/'soak_relay.py'),'exec'))

