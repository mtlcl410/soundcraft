from pathlib import Path
import time,re,shutil,os,subprocess
d=Path(__file__).parent
for i in range(240):
 s=(d/'build.log').read_bytes()
 if b'\x00' in s:
  s=s.decode('utf-16')
 else:s=s.decode('utf-8-sig',errors='replace')
 m=re.search(r'Executable unittests .*?\((.*?\.exe)\)',s)
 if m:break
 if 'could not compile' in s or 'error[E' in s:raise RuntimeError(s[-1500:])
 time.sleep(2)
else:raise RuntimeError('build timeout')
src=Path(m[1]);src=src if src.is_absolute() else d/'repo'/src
exe=d/'dj-audit.exe';shutil.copyfile(src,exe)
print(exe,flush=True)
with (d/'run.log').open('w') as h:
 result=subprocess.run([str(exe),'local_dj_scenario_matrix','--ignored','--nocapture'],cwd=d/'repo',env=os.environ|{'DJ_AUDIT':str(d)},stdout=h,stderr=subprocess.STDOUT)
print(result.returncode)
