"""Time to lock is measured from the first received quarter-frame and from the master's labels."""
from pathlib import Path
import csv,json,sys
out=Path(__file__).resolve().parent
root=out.parents[1]
def read(r):return json.loads(r.read_text())
def measure(folder):
    items=read(folder/'marker-phase.json')
    seg=read(folder/'segments.json')
    with (folder/'wire.csv').open() as f:
        wire=[(int(r['qpc_ns']),bytes.fromhex(r['hex'])) for r in csv.DictReader(f)]
    rows=[]
    for s,r in zip(seg,items,strict=True):
        prior=[msg for t,msg in wire if t<s['first'] and msg.startswith(b'\xf0\x7f') and len(msg)==10]
        if not prior:raise ValueError('No preceding locate')
        h,m,sec,frame=prior[-1][5:9]
        assert h>>5==3,'This comparison uses 30 fps'
        locate=(h&31)*3600+m*60+sec+frame/30
        q=[(t,msg[1]) for t,msg in wire if s['first']<=t<=s['last'] and msg[0]==0xf1]
        assert [v>>4 for _,v in q[:16]]==list(range(8))*2
        label_origin=r['origin_qpc_s']+locate
        lead=(q[0][0]/1e9-label_origin)*1000
        duration=(q[15][0]-q[0][0])/1e6
        mk=r['markers'][0]
        rows.append(dict(locate=locate,first_frame=r['first_frame'],first_label_minus_locate_frames=r['first_frame']-round(locate*30),
                         locate_origin_to_first_wire_ms=round(lead,4),first_wire_to_confirm_ms=round(duration,4),
                         tx_offset_vs_labels_ms=mk['tx']['ms'],tx_offset_vs_first_wire_ms=round(mk['tx']['ms']-lead,4),
                         rx_offset_vs_labels_ms=mk['rx']['ms'],rx_offset_vs_first_wire_ms=round(mk['rx']['ms']-lead,4)))
    return rows
if __name__=='__main__':
    folders=[root/'runs/h4b-model12-02',root/'runs/h4a-integration-30-forward-01',root/'runs/h4a-integration-30-reverse-01']
    data={p.name:measure(p) for p in folders}
    print(json.dumps(data[folders[0].name],indent=2))
    for n,rs in data.items():print(n,[(k,min(r[k] for r in rs),max(r[k] for r in rs)) for k in ('first_label_minus_locate_frames','first_wire_to_confirm_ms','tx_offset_vs_first_wire_ms','rx_offset_vs_first_wire_ms')])
    (out/'start-references.json').write_text(json.dumps(data,indent=2))

