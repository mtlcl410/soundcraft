import ctypes as c
from ctypes import wintypes as w
system=c.windll.ntdll.NtQuerySystemInformation
buffer=c.create_string_buffer(8*1024*1024)
def proc_times():
 global buffer
 n=w.ULONG()
 code=system(5,buffer,len(buffer),c.byref(n))
 if code:
  if n.value <= len(buffer): raise OSError(code)
  buffer=c.create_string_buffer(n.value+1024*1024)
  if system(5,buffer,len(buffer),c.byref(n)): raise OSError('process snapshot')
 base=c.addressof(buffer); data={}; off=0
 while off+96<=n.value:
  addr=base+off
  nxt=w.DWORD.from_address(addr).value
  length=w.USHORT.from_address(addr+56).value
  string=c.c_void_p.from_address(addr+64).value
  pid=c.c_void_p.from_address(addr+80).value or 0
  ticks=c.c_int64.from_address(addr+40).value+c.c_int64.from_address(addr+48).value
  name=c.wstring_at(string,length//2).lower() if string and length else 'idle'
  data[pid]=name,ticks/1e7
  if not nxt:break
  off+=nxt
 return data
if __name__=='__main__':
 import psutil,time,os
 p=psutil.Process(); start=time.perf_counter()
 for _ in range(60):s=proc_times()
 print(len(s),'snapshot_ms',(time.perf_counter()-start)/60*1000,'self',s[os.getpid()],p.cpu_times())
