from pathlib import Path
import json, time
r=Path(__file__).resolve().parent
until=time.monotonic()+55
p=r/'take1-wire.jsonl'
while p.stat().st_size<7000 and time.monotonic()<until: time.sleep(.6)
import subprocess,sys
subprocess.call([sys.executable,'-X','utf8',str(r/'read.py'),'take1'])
