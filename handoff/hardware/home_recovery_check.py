"""Check native stream cadence and A4 integrity after the three physical resets."""
import json,sys
from pathlib import Path

def check_window(h):
    return (1400 <= h['intervals'] and abs(h['mean']-1000*256/48000)<=.05*1000*256/48000
            and sum(h['bins'][6:])==0 and len(h['segments'])==1
            and all(s['rate']==48000 and s['buffer']==256 and s['sample_jumps']==0 and s['seq_skips']==0 for s in h['segments']))

def score(path):
    hist=json.loads((path/'histograms.json').read_text())
    tones=json.loads((path/'a4.json').read_text())
    rows={}
    for key in ['play-baseline','play-1','play-2','play-3']:
        h=hist[key]; t=tones[key]
        q=[t[ch]['correlation'] for ch in ['out1','in9']]
        rows[key]=dict(cadence=check_window(h),intervals=h['intervals'],mean_ms=h['mean'],bins=h['bins'],
                       a4_match=all(v is not None and v>.99 for v in q),a4_scores=q,
                       roundtrip_ms=(t['in9']['window_s']-t['out1']['window_s'])*1000)
    result=dict(windows=rows,within_3ms_of_baseline=all(abs(r['roundtrip_ms']-rows['play-baseline']['roundtrip_ms'])<=3 for r in rows.values()))
    (path/'recovery-check.json').write_text(json.dumps(result,indent=2))
    return all(r['cadence'] and r['a4_match'] for r in rows.values()) and result['within_3ms_of_baseline']
if __name__=='__main__':sys.exit(0 if score(Path(sys.argv[1])) else 1)

