import json
from pathlib import Path
from statistics import median
import sys

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(folder.parent/'capture-deps'))
import numpy as np

def summary(root):
    rows = []
    for i in range(1,4):
        j = json.loads((root/f'cal-{i}-result.json').read_bytes())
        kick,hat = np.array(j['kick']),np.array(j['hat'])
        assert len(kick)==48 and len(hat)==96
        beat = np.r_[np.diff(kick),np.median(np.diff(kick)[-5:])]
        ideal = np.column_stack((kick, kick+.5*beat)).flatten()
        mids = (ideal[1:] + ideal[:-1])/2
        assert np.array_equal(np.searchsorted(mids,hat), np.arange(96))
        assert j['controls']==[[250],[252]] and j['stopped']
        assert max(abs(np.array(j['bpms'])-[80,130,80])) < 1
        quarter = (hat[::2]-kick)*1000
        ideal_kick=np.r_[np.repeat(.75,16),np.repeat(60/130,16),np.repeat(.75,15)]
        assert max(abs(np.diff(kick)-ideal_kick))<.020
        row = {'take':i, 'wire_bpm':j['bpms'],'peak':j['peak'],'section_counts':[[16,32]]*3}
        for ix,tag in [(16,'speed_up'),(32,'slow_down')]:
            before=median(quarter[ix-8:ix-1])
            delta=(hat[2*ix:2*ix+16]-ideal[2*ix:2*ix+16])*1000-before
            row[tag]={'next_beat_ms':round(delta[2],2),'first_offbeat_ms':round(delta[1],2),'max_first_two_bars_ms':round(max(abs(delta)),2),
                      'last_four_beats_ms':round(median(quarter[ix+12:ix+16])-before,2)}
        rows.append(row)
    return rows

if __name__=='__main__':
    report = {k:summary(p) for k,p in [('before',folder),('intermediate',folder/'fixed'),('after',folder/'final')] if (p/'cal-3-result.json').is_file()}
    print(json.dumps(report,indent=2))
    (folder/'comparison.json').write_text(json.dumps(report,indent=2))
