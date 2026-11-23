from pathlib import Path
import sys,subprocess,time,os,json
d=Path(__file__).resolve().parent
tag=sys.argv[1]
assert tag.isalnum()
p=d/tag
p.mkdir(exist_ok=False)
flag=p/'end.flag'
tools=[('wire',[str(d/'tap.exe'),str(p/'ready'),str(flag),str(p/'wire.csv')]),('status',[sys.executable,'-u',str(d/'capture.py'),tag]),('input',[str(d/'phase-audio.exe'),'input',str(p/'input'),str(flag)]),('loop',[str(d/'phase-audio.exe'),'loop',str(p/'loop'),str(flag)])]
cs=[]
try:
 for name,args in tools:
  log=(p/(name+'.log')).open('wb')
  proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,cwd=d)
  cs.append((name,proc))
 for n in range(80):
  for name,proc in cs:
   if proc.poll() is not None: raise RuntimeError(f"{name} exited {proc.returncode}")
  if (p/'ready').exists() and all((p/(x+'.csv')).exists() for x in ['input','loop']) and 'READY' in (p/'status.log').read_text(errors='replace'): break
  time.sleep(.2)
 else: raise RuntimeError('recorders failed readiness check')
 print("CAPTURE READY",tag,flush=True)
 deadline=time.monotonic()+1190
 while not flag.exists() and time.monotonic()<deadline and all(proc.poll() is None for name,proc in cs):
  time.sleep(.5)
finally:
 flag.touch()
 (d/(tag+'.end')).touch()
 for name,proc in cs: print(name,proc.wait(timeout=15),flush=True)
