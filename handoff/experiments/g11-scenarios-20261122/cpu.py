import os, ctypes, subprocess, time
from ctypes import wintypes as wt
from pathlib import Path
d=Path(__file__).resolve().parent
get=ctypes.windll.kernel32.GetProcessTimes
get.argtypes=[wt.HANDLE]+[ctypes.POINTER(wt.FILETIME)]*4
def seconds(t):return ((t.dwHighDateTime<<32)+t.dwLowDateTime)/1e7
with (d/'c7-final.log').open('w',encoding='utf-8') as log:
    for inserts in (0,2,6):
        begin=time.perf_counter()
        with subprocess.Popen([str(d/'load-bench.exe'),'scenario_c7_chase','--ignored','--nocapture','--test-threads=1'],env=dict(os.environ, SCENARIO_C7_INSERTS=str(inserts)),stdout=log,stderr=log) as proc:
            proc.wait()
            wall=time.perf_counter()-begin
            ts=[wt.FILETIME() for _ in range(4)]
            assert get(wt.HANDLE(int(proc._handle)),*[ctypes.byref(t) for t in ts])
            cpu=seconds(ts[2])+seconds(ts[3])
            print(f'C7 inserts={inserts} process_cpu_seconds={cpu:.4f} wall={wall:.4f} percent_of_one_logical_core={100*cpu/wall:.1f} exit={proc.returncode}',file=log,flush=True)
