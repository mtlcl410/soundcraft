import re, ast, sys
from pathlib import Path
p=Path(sys.argv[1])
s=p.read_text(encoding='utf-8-sig')
a=re.search(r'slowdown signed_ms=(\[[^\]]+\])',s)
values=ast.literal_eval(''.join(a[1].split()))
print(f'{p.name}: first offbeat {values[1]:+.3f} ms, max from second beat {max(map(abs,values[2:])):.3f} ms')
assert abs(values[1])<=10. and all(abs(value)<=4. for value in values[2:]), '130 -> 80 after eight bars: first offbeat <= 10 ms and from second beat <= 4 ms'

