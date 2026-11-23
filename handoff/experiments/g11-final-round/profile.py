"""Invoke the requested ignored profiles and capture peak working set for the suite under test."""
from pathlib import Path
import subprocess,sys,os,json,time
from ctypes import wintypes as W
import ctypes as C
class Counters(C.Structure):
 _fields_=[('cb',W.DWORD),('PageFaultCount',W.DWORD),*[(k,C.c_size_t) for k in ['peak','working','qpp','qp','qnp','qn','file','peakfile']]]
def working(proc):
 h=C.windll.kernel32.OpenProcess(0x410,False,proc.pid)
 try:
  i=Counters(); i.cb=C.sizeof(i)
  return i.peak if h and C.windll.psapi.GetProcessMemoryInfo(h,C.byref(i),i.cb) else None
 finally:
  if h: C.windll.kernel32.CloseHandle(h)
def profile(exe,filter,out,ignored):
 with out.open('wb') as f:
  args=[str(exe),filter,'--nocapture','--test-threads=1']
  if ignored:args+=['--ignored']
  proc=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT)
  rss=0;start=time.monotonic()
  while proc.poll() is None:
   rss=max(rss,working(proc) or 0);time.sleep(.1)
 return dict(argv=args,code=proc.returncode,peak_working_bytes=rss,seconds=time.monotonic()-start,log=out.name)
if __name__=='__main__':
 exe,term,out,ignored=sys.argv[1:]
 r=profile(Path(exe).resolve(),term,Path(out),ignored=='ignored')
 Path(out+'.json').write_text(json.dumps(r,indent=2))
 print(r,flush=True)
 sys.exit(r['code'])
