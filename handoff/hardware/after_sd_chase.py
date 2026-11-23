"""Keep the operator's single panel session moving after M-3 releases the ASIO device."""
import json,subprocess,sys,time
from pathlib import Path
hw=Path(__file__).resolve().parent
m3=hw/'runs/m3-sd-01'
until=time.monotonic()+780
while not (m3/'environment-result.json').exists():
    if time.monotonic()>until:raise TimeoutError('M-3 did not finish')
    time.sleep(.5)
if not (m3/'stopped.json').exists():raise RuntimeError('M-3 stopped prematurely')
print('M-3 environment:',(m3/'environment-result.json').read_text(),flush=True)
with (m3/'pc-marker-check.log').open('wb') as log:
    job=subprocess.run([sys.executable,'m3_pc_check.py',str(m3)],cwd=hw,stdout=log,stderr=subprocess.STDOUT)
print('PC signal check:',job.returncode,flush=True)
panel=json.loads((hw/'panel.json').read_text('utf-8-sig'))
panel.update(midi_timecode='OFF at recorder preparation; operator enables for the three rolls, confirmed by wire and operator',midi_clock_spp='OFF',test='H-4b, M-3 SD song')
pf=hw/'panel-h4b.json'
pf.write_text(json.dumps(panel,indent=2))
sys.exit(subprocess.call([sys.executable,'environment.py','run','--panel',str(pf),'--out','runs/h4b-model12-02','--audio','--',sys.executable,'manual_run.py','manual'],cwd=hw))

