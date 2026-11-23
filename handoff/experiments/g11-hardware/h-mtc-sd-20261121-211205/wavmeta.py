from pathlib import Path
import struct,sys
p=Path(sys.argv[1])
with p.open('rb') as f:
 f.read(12)
 while h:=f.read(8):
  k,n=struct.unpack('<4sI',h)
  print(k,n,f.tell(),end=' ')
  if k==b'bext':
   b=f.read(n); print('TimeReference',struct.unpack_from('<Q',b,338)[0])
  elif k==b'data': f.seek(n,1); print('samples')
  else: print(f.read(min(32,n)).hex());f.seek(max(0,n-32),1)
  if n%2:f.read(1)
