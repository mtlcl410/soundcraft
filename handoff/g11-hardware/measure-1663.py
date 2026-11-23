from pathlib import Path
import subprocess
h=Path(__file__).resolve().parent
with (h/'1663-perf-comparison.log').open('w') as f:
 for i in range(3):
  for name in (['before','after'] if i%2==0 else ['after','before']):
   print('RUN',i+1,name,file=f,flush=True)
   subprocess.run([str(h/f'1663-review-{name}.exe'),'review_measure','--nocapture','--test-threads=1'],stdout=f,stderr=subprocess.STDOUT,check=True)
