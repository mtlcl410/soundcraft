"""Validate continuity and histogram the ASIO driver's monotonic callback times, without loading the PCM."""
from pathlib import Path
import json,sys
a=Path(__file__).resolve().parent
sys.path.insert(0,str(a.parent.parent/'g11-hardware/capture-deps'))
import numpy as np
p=Path(sys.argv[1]);meta,=(p/'driver').glob('epoch-*.json');m=json.loads(meta.read_text())
dtype=np.dtype(dict(names=['pos','qpc','serial','flags','n'],formats=['<u8','<u8','<u8','<i4','<u4'],offsets=[0,16,24,32,36],itemsize=40+8*m['buffer']))
q=np.memmap(meta.with_suffix('.bin'),dtype=dtype,mode='r')
times=np.copy(q['qpc']).astype('int64'); gap=np.diff(times)*1000./m['qpc_frequency']
limits=[0,4,7,10,20,100,200,300,np.inf]; hist=np.histogram(gap,bins=limits)[0]
result=dict(buffer=m['buffer'],rate=m['sample_rate'],count=len(q),min_ms=gap.min(),mean_ms=gap.mean(),
    median_ms=np.median(gap),p99_ms=np.percentile(gap,99),p999_ms=np.percentile(gap,99.9),max_ms=gap.max(),
    position_discontinuities=int(np.count_nonzero(np.diff(q['pos'])!=m['buffer'])),
    serial_discontinuities=int(np.count_nonzero(np.diff(q['serial'])!=1)),
    invalid_samplepos=int(np.count_nonzero((q['flags'] & 2)==0)),
    unexpected_buffer=int(np.count_nonzero(q['n']!=m['buffer'])),negative_intervals=int(np.count_nonzero(gap<0)),
    histogram={f'[{lo}, {hi})':int(n) for lo,hi,n in zip(limits,limits[1:],hist)})
(p/'asio-callback-histogram.json').write_text(json.dumps(result,indent=2));print(result)
