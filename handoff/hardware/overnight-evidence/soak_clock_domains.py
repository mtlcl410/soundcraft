"""Measure independent hardware and wire clocks over common interior windows; no nearest-pulse matching."""
import csv, json, struct, sys
from pathlib import Path
from bisect import bisect_left
from statistics import median

def measure(p):
    meta, = (p/'driver').glob('epoch-*.json')
    m=json.loads(meta.read_text()); fmt=struct.Struct('<QQQQiI')
    size=fmt.size+m['buffer']*8; wav=meta.with_suffix('.bin'); count,rem=divmod(wav.stat().st_size,size)
    assert not rem
    def read_wire(file,kind):
        with (p/file).open() as f:
            return [int(r['at_ns']) for r in csv.DictReader(f) if r['hex'].startswith(kind)]
    ins=read_wire('ingress.csv','f8');outs=read_wire('egress.csv','f8');qfs=read_wire('egress.csv','f1')
    rows=[]
    with wav.open('rb') as w:
        def block(i):
            w.seek(i*size); pos,_,qpc,serial,flags,n=fmt.unpack(w.read(fmt.size))
            assert flags&2 and n==m['buffer']
            return qpc*1_000_000_000//m['qpc_frequency'],pos
        def estimate(timestamp):
            lo=0;hi=count-1
            while hi-lo>1:
                j=(lo+hi)//2
                if block(j)[0]<=timestamp:lo=j
                else:hi=j
            left=max(0,lo-24);right=min(count-1,hi+24)
            t0,s0=block(left);t1,s1=block(right)
            assert t0<=timestamp<=t1 and s1-s0==(right-left)*m['buffer']
            return s0+(timestamp-t0)*(s1-s0)/(t1-t0)
        # Bound both ends to real ingress F8, leaving at least 1 s beyond each boundary.
        span=28800 if len(ins)>58000 else (len(ins)-96)//2
        for offset in range(48,len(ins)-span-48,span):
            end=offset+span;t0,t1=ins[offset],ins[end];sec=(t1-t0)/1e9
            frames=estimate(t1)-estimate(t0)
            q=bisect_left(qfs,t1)-bisect_left(qfs,t0); c=bisect_left(outs,t1)-bisect_left(outs,t0)
            rows.append(dict(input_start=offset,input_stop=end,wall_s=sec,pcm_frames=frames,
                effective_hz=frames/sec,device_ppm=1e6*(frames/sec/m['sample_rate']-1),
                input_f8=span,output_f8=c,quarter_frames=q,wire_time_excess_ms=(sec-span/48)*1000,
                device_excess_ms=(frames/m['sample_rate']-sec)*1000, f8_excess=c-span,
                qf_excess=q-span*2.5))
    assert rows
    total=sum(r['wall_s'] for r in rows)
    pred=sum(r['device_excess_ms'] for r in rows)
    return dict(common_window_s=total,windows=rows,median_device_ppm=median(r['device_ppm'] for r in rows),
        device_excess_ms=pred,relative_to_wall_expected_extra_f8=pred*.048,
        relative_to_wall_expected_extra_qf=pred*.12,observed_extra_f8=sum(r['f8_excess'] for r in rows),
        observed_extra_qf=sum(r['qf_excess'] for r in rows))
if __name__=='__main__':
    p=Path(sys.argv[1]);result=measure(p);(p/'counter-domains.json').write_text(json.dumps(result,indent=2))
    print({k:v for k,v in result.items() if k!='windows'})
