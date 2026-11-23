import ctypes as c
from ctypes import wintypes as wt
import pathlib,re,psutil,subprocess,time,json
root=pathlib.Path(__file__).resolve().parent
k=c.WinDLL('kernel32',use_last_error=True)
k.OpenThread.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD];k.OpenThread.restype=wt.HANDLE
k.GetThreadDescription.argtypes=[wt.HANDLE,c.POINTER(c.c_void_p)]
k.QueryThreadCycleTime.argtypes=[wt.HANDLE,c.POINTER(c.c_ulonglong)]
k.GetThreadTimes.argtypes=[wt.HANDLE]+[c.POINTER(c.c_uint64)]*4
k.LocalFree.argtypes=[c.c_void_p];k.CloseHandle.argtypes=[wt.HANDLE]
def name(h):
    v=c.c_void_p()
    if k.GetThreadDescription(h,c.byref(v))==0 and v.value:
        n=c.wstring_at(v);k.LocalFree(v);return n
def usage(h):
    f=[c.c_uint64() for _ in range(4)]; assert k.GetThreadTimes(h,*map(c.byref,f))
    cycles=c.c_ulonglong();assert k.QueryThreadCycleTime(h,c.byref(cycles))
    return {'cpu_ms':(f[2].value+f[3].value)/10000,'cycles':cycles.value}
build=(root/'review-final-bench-build.log').read_text(encoding='utf-8-sig')
exe=re.findall(r'\(([^()\n]+\.exe)\)',build)[-1]
handles={}
with (root/'review-worker-cpu-bench.log').open('w') as log:
    proc=subprocess.Popen([exe,'perf_review::worker_timing','--test-threads=1','--nocapture'],stdout=log,stderr=subprocess.STDOUT)
    process=psutil.Process(proc.pid)
    while proc.poll() is None:
        for thread in process.threads():
            if thread.id in handles: continue
            h=k.OpenThread(0x0800,False,thread.id)
            if h:
                n=name(h)
                handles[thread.id]=(n,h)
        time.sleep(.2)
result=[]
for tid,(n,h) in handles.items():
    stamps=[c.c_uint64() for _ in range(4)]
    assert k.GetThreadTimes(h,*map(c.byref,stamps))
    dt=(stamps[1].value-stamps[0].value)/1e7
    result.append(dict(tid=tid,name=n,start=stamps[0].value,seconds=dt,**usage(h)))
result.sort(key=lambda row:row['start'])
for n,h in handles.values(): k.CloseHandle(h)
(root/'review-final-worker-cpu.json').write_text(json.dumps(result,indent=2))
assert proc.returncode==0
