"""Separate relay latency, the observed output transport Stop, and trailing timing messages."""
import csv,json,sys
from pathlib import Path
def read(path,key):
    with path.open() as f:
        return [(int(r[key]),r['hex']) for r in csv.DictReader(f)]
def analysis(p):
    # Read only the tail on the lengthy takes; the exercise is the final Stop of one pass.
    from collections import deque
    def tail(name,key):
        with (p/name).open() as f:
            return [(int(r[key]),r['hex']) for r in deque(csv.DictReader(f),maxlen=128)]
    phys=tail('relay.csv','arrival_ns');received=tail('ingress.csv','at_ns');returned=tail('egress.csv','at_ns')
    def stop(lst):return next(t for t,msg in reversed(lst) if msg=='fc')
    wire,app,out=stop(phys),stop(received),stop(returned)
    data=dict(physical_to_virtual_fc_ms=(app-wire)/1e6,virtual_fc_to_returned_fc_ms=(out-app)/1e6)
    for label,typ in [('clock','f8'),('qf','f1')]:
        packets=[t for t,msg in returned if msg.startswith(typ)]
        data[label]=dict(last_minus_virtual_fc_ms=(packets[-1]-app)/1e6,
                         received_between_virtual_and_returned_fc=sum(app<t<=out for t in packets),
                         received_after_returned_fc=sum(out<t for t in packets))
    return data
if __name__=='__main__':
    for path in map(Path,sys.argv[1:]):
        r=analysis(path);(path/'stop-stages.json').write_text(json.dumps(r,indent=2));print(path.name,r)
