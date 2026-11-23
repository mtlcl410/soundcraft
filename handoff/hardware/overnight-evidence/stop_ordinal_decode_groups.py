"""Decode complete 30 fps MTC addresses; preserve any partial group at the final FC."""
from audit_mtc_clock_domains import frames
import csv, json, sys
from pathlib import Path
p=Path(sys.argv[1])
start=None
last=None
groups=0
wrong_step=0
pieces=[]
partials=[]
full=[]
with (p/'egress.csv').open() as f:
    for row in csv.DictReader(f):
        m=bytes.fromhex(row['hex'])
        if m==b'\xfc' and pieces:
            partials.append(dict(piece_indices=list(range(len(pieces))), nibbles=pieces))
            pieces=[]
        elif m.startswith(bytes.fromhex('f07f7f0101')):
            full.append(frames(*m[5:9]))
        elif m[0]==0xf1:
            k,n=divmod(m[1],16)
            assert k==len(pieces)
            pieces.append(n)
            if k==7:
                fr,sec,minute,hour=[pieces[i]+16*pieces[i+1] for i in (0,2,4,6)]
                label=frames(hour,minute,sec,fr)
                if last is not None and label!=last+2: wrong_step+=1
                if start is None: start=label
                last=label
                groups+=1
                pieces=[]
v=dict(complete_groups=groups,first_address=start,last_complete_address=last,
       non_two_frame_steps=wrong_step,partial_groups_at_fc=partials,
       pieces_after_final_transport=len(pieces),full_frame_addresses=full)
assert 8*groups+sum(len(t['nibbles']) for t in partials)+len(pieces)==json.loads((p/'result.json').read_text())['received_qf']
(p/'qf-complete-and-partial.json').write_text(json.dumps(v,indent=2))
print(json.dumps(v))

