"""Compare pitched portions of every matching hardware note against the local instrument take."""
from acquisition_analysis import *
reference='smu-phase-reference-1795133302896796600'

def note_windows(base):
    a=json.loads((root/(base+'-acquisition.json')).read_text())
    meta=json.loads((root/(base+'.json')).read_text())
    n=Tap(list(records(root/(base+'-native.bin'))),meta['wall_qpc_offset_ns'])
    result=[]
    size=2048
    window=np.hanning(size)
    for note in a['notes']:
        hz=440*2**((note['expected_pitch']-69)/12)
        low=int(hz*2**(-1.5/12)*16384/rate)
        high=int(np.ceil(hz*2**(1.5/12)*16384/rate))
        cents=[]
        for dt in [.050,.075,.100,.125,.150]:
            t=note['qpc']+dt
            block=np.searchsorted(n.dev,t,side='right')-1
            center=int(n.starts[block]+round((t-n.dev[block])*rate))
            y=n.y[center-size//2:center+size//2]
            spec=abs(np.fft.rfft(y*window,16384))
            k=low+int(spec[low:high+1].argmax())
            assert low<k<high,(note['score_seconds'],k,low,high)
            l,m,r=np.log(np.maximum(spec[k-1:k+2],1e-20))
            fundamental=(k+.5*(l-r)/(l-2*m+r))*rate/16384
            cents.append(1200*np.log2(fundamental/hz))
        result.append(dict(sec=note['score_seconds'],pitch=note['expected_pitch'],cents=cents))
    return a,result

def compare(base):
    a,notes=note_windows(base);ref,local=note_windows(reference)
    rows=[]
    for n,r in zip(notes,local):
        assert (n['sec'],n['pitch'])==(r['sec'],r['pitch'])
        diff=np.array(n['cents'])-r['cents']
        rows.append(dict(sec=n['sec'],median_cents=round(float(np.median(diff)),2),worst_abs_cents=round(float(abs(diff).max()),2),windows=[round(float(x),2) for x in diff]))
    report=dict(recording=base,reference=reference,window_centers_ms=[50,75,100,125,150],rows=rows,
        max_abs_note_median=max(abs(r['median_cents']) for r in rows),max_abs_window=max(r['worst_abs_cents'] for r in rows))
    (root/(base+'-pitch.json')).write_text(json.dumps(report,indent=2))
    print(base,report['max_abs_note_median'],report['max_abs_window'],[(r['sec'],r['median_cents']) for r in rows[:12]])
if __name__=='__main__':
    for arg in sys.argv[1:]:compare(arg)

