"""Exercise four external Stop phases on each compensation setting on the same two DIN paths."""
import csv
import json
import os
from pathlib import Path
import re
import sys
from statistics import median
from cue_hardware import run
from stop_ordinal_replay import decode

here=Path(__file__).resolve().parent

def measure(label, mode, advance):
    folder = here/label
    def read(name):
        return json.loads((folder/name).read_text(encoding='utf-8-sig'))
    result = read('result.json')
    environment = read('environment-result.json')
    port = result['status']['output']['ports']['UM-ONE']
    assert read('compensation-verified.json')['settings']['compensation']['beat_clock'] == (mode=='on')
    assert read('source-stop.json')['advance_ms'] == advance
    source, launch = decode(folder/'ingress.csv')
    heard, returned = decode(folder/'egress.csv')
    log = (folder/'application.log').read_text(errors='replace')
    stamps = [list(map(int, sample)) for sample in re.findall(r'SC_STOP_QPC (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',log)
              if int(sample[0]) > 0]
    origin, host, callback, last_begin, last_end, fc_begin, fc_end = stamps[-1]
    drops = [dict(at_ms=(int(at)-origin)/1e6,pass_id=int(p),ordinal=int(ordinal),source_last=int(last))
             for at,p,ordinal,last in re.findall(r'SC_STOP_CUTOFF (\d+) (\d+) (\d+) (\d+)',log)]
    with (folder/'egress.csv').open() as f:
        rows=list(csv.DictReader(f))
    fc=next(int(r['at_ns']) for r in rows if r['hex']=='fc')
    clocks=[int(r['at_ns']) for r in rows if r['hex']=='f8']
    valid=(environment['environment_valid'] and source==list(range(576)) and result['physical_input']==len(source)
           and launch==returned==['fa','fc'] and result['dropout_count']==0 and len(stamps)==1)
    return dict(label=label, valid=valid, mode=mode, advance_ms=advance, input=len(source), output=len(heard),
                valid_prefix=(heard[:len(source)] == source), omitted=max(0,len(source)-len(heard)),surplus=max(0,len(heard)-len(source)),
                suppressions=drops,last_send_begin_ms=(last_begin-origin)/1e6,last_send_end_ms=(last_end-origin)/1e6,
                returned_after_output_stop=sum(t>fc for t in clocks),qf=result['received_qf'],steady_median_spacing_ms=median(
                    (y-x)/1e6 for x,y in zip(clocks[48:-49],clocks[49:-48])),effective_clock_offset_us=port['beat_clock_total_us'],
                compensation_readback=read('compensation-verified.json')['settings']['compensation'])

if __name__=='__main__':
    sha=sys.argv[1]
    result=[]
    # Reverse the phase sequence in the second block.
    for mode, phases in [('on',(0,5,10,15)), ('off',(15,10,5,0))]:
        for advance in phases:
            os.environ.update(SC_AUDIT_STOP_ADVANCE_MS=str(advance),SC_AUDIT_BEAT_COMPENSATION=mode)
            label=f'stop-ordinal-{sha}-{mode}-{advance}'
            run(label,sha+'-build.json',12)
            row=measure(label,mode,advance)
            result.append(row)
            (here/(f'stop-ordinal-matrix-{sha}.json')).write_text(json.dumps(result,indent=2))
            print(row,flush=True)
            if not row['valid']:
                raise RuntimeError('Invalid trial '+label)

