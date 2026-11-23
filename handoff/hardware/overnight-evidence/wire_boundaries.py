"""Characterize startup/stop counts with unmodified physical timestamps on a shared host clock."""
from bisect import bisect_left
import csv
import json
from pathlib import Path
import sys

def assign_nearest(input_pulses, output_pulses, period):
    """Allow at most half an ideal period. Unmatched observations remain visible."""
    if not input_pulses:
        raise ValueError("No reference F8")
    used=set(); extra=[]; duplicates=0; ties=0; errors=[]
    for at in output_pulses:
        j=bisect_left(input_pulses,at)
        candidates = [i for i in (j-1,j) if 0<=i<len(input_pulses)]
        candidates.sort(key=lambda i:abs(input_pulses[i]-at))
        i=candidates[0]; delta=at-input_pulses[i]
        if len(candidates)==2 and abs(delta)==abs(input_pulses[candidates[1]]-at):
            ties+=1
            continue
        if abs(delta)*2>period:
            extra.append(at)
            continue
        if i in used:
            duplicates+=1
            continue
        used.add(i);errors.append(delta)
    missing=set(range(len(input_pulses)))-used
    first,last=(min(used),max(used)) if used else (None,None)
    return dict(matched=len(used),missing=len(missing),first_matched=first,last_matched=last,
        missing_inside_matched_span=sum(first<i<last for i in missing) if used else None,
        repeated_nearest_input=duplicates,equidistant=ties,outside_half_period=len(extra),
        outside_after_last=sum(at>input_pulses[-1] for at in extra),
        median_matched_error_ms=sorted(errors)[len(errors)//2]/1e6 if errors else None)

def data(p):
    def read(name):
        with (p/name).open() as f:
            return [(int(r['at_ns']),bytes.fromhex(r['hex'])) for r in csv.DictReader(f)]
    ingress=read('ingress.csv'); output=read('egress.csv')
    pulses=[t for t,m in ingress if m==b'\xf8']; sent=[t for t,m in output if m==b'\xf8']
    start=next(t for t,m in ingress if m==b'\xfa')
    stop=next(t for t,m in ingress if m==b'\xfc')
    qf=[(t,m[1]) for t,m in output if len(m)==2 and m[0]==241]
    result=assign_nearest(pulses,sent,1_000_000_000/48)
    result.update(reference='120 BPM; independently nearest input within half a pulse. After long source gaps pulse identity is ambiguous.',
                  first_clock_after_input_start_ms=(sent[0]-start)/1e6,last_clock_minus_input_stop_ms=(sent[-1]-stop)/1e6,
                  first_qf_after_input_start_ms=(qf[0][0]-start)/1e6,last_qf_minus_input_stop_ms=(qf[-1][0]-stop)/1e6,
                  first_qf_piece=qf[0][1]>>4,last_qf_piece=qf[-1][1]>>4,
                  qf_piece_discontinuities=sum((y[1]>>4)!=(1+(x[1]>>4))%8 for x,y in zip(qf,qf[1:])),
                  qf_qualification='An entire eight-piece sequence may be missing without a piece-index discontinuity.')
    return result

if __name__=='__main__':
    p=Path(sys.argv[1]);result=data(p);(p/'edge-analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
