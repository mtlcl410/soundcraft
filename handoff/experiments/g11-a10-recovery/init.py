from pathlib import Path
import re
d=Path(__file__).resolve().parent
s=d.parent/'g11-scenarios-20261122'
def extract(file,name):
 t=(s/file).read_text(encoding='utf-8')
 return t[t.index('+#[test]\n+fn '+name):].split('\n+}',1)[0].replace('\n+','\n')[1:]+'\n}\n'
clock=extract('local-tests-1662.patch','a10_first_clock').replace('test_rate(48000)','soundcraft_time::SampleRate::HZ_48000')
dual=extract('local-tests-1663.patch','scenario_a10_dual')
for name in ['main','beat','mtc','follow']:
 p=d/name/'crates/playback/src'
 for file,test in [('sync_output_tests.rs',clock),('mtc_sync_output_tests.rs',dual)]:
  f=p/file
  if not f.exists():
   print(name,file,'N/A - no production output/test module')
   continue
  with f.open('a',encoding='utf-8') as fp:fp.write('\n'+test)
