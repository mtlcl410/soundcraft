"""Forecast independent event counts on held-out windows; no device-specific constants."""
import json
from pathlib import Path
import sys

def compare(rows):
    if len(rows)<2:
        raise ValueError('requires separate training and test windows')
    initial=rows[0]['effective_hz']/48000.
    held=rows[1:]
    elapsed=sum(r['wall_s'] for r in held)
    earned=elapsed*(initial-1.)
    f8=sum(r['f8_excess'] for r in held); qf=sum(r['qf_excess'] for r in held)
    return dict(training_seconds=rows[0]['wall_s'],training_ppm=(initial-1)*1e6,
        held_out_seconds=elapsed,observed_clock_excess=f8,observed_qf_excess=qf,
        prediction_extra_clock=earned*48,prediction_extra_qf=earned*120,
        clock_residual=f8-earned*48,qf_residual=qf-earned*120,
        device_excess_minus_prediction_ms=sum(r['device_excess_ms'] for r in held)-1000*earned)

if __name__=='__main__':
    p=Path(sys.argv[1]);v=compare(json.loads((p/'counter-domains.json').read_text())['windows'])
    (p/'counter-holdout.json').write_text(json.dumps(v,indent=2));print(v)
