from run_edm import audio, d, np, json, RATE
from assess import matches,mono
from pathlib import Path
import sys, wave

def count(x,part,threshold):
    needle=mono(d/(part+'.wav'))[200:1600]
    s=matches(x,needle)
    ix=np.flatnonzero(s>threshold)
    groups=np.split(ix,np.flatnonzero(np.diff(ix)>4800)+1) if len(ix) else []
    return np.array([(g[s[g].argmax()]-200)/RATE for g in groups])

def verify(root):
    with wave.open(str(root/'mix-1.wav')) as w:
        x=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float).reshape(-1,2)
    kick=count(x[:,0],'Kick',.85)
    backbeat=count(x[:,0],'Snare',.70)
    hat=count(x[:,1],'Hat',.55)
    crash=count(x[:,1],'Crash',.70)
    assert len(kick)==24 and len(backbeat)==24 and len(hat)==96 and len(crash)==2
    beats=np.sort(np.r_[kick,backbeat])
    assert np.array_equal(beats[::2],kick)
    assert np.max(np.abs(np.diff(beats)-np.r_[np.repeat(.75,16),np.repeat(60/130,16),np.repeat(.75,15)]))<.020
    assert np.max(abs(crash-beats[[16,32]]))<.12
    even_hat_expected=beats
    odd_hat_expected=beats+np.r_[np.diff(beats),.75]/2
    expect=np.column_stack([even_hat_expected,odd_hat_expected]).flatten()
    assert np.array_equal(np.searchsorted((expect[1:]+expect[:-1])/2,hat),np.arange(96))
    wire=json.loads((root/'mix-1-result.json').read_bytes())
    assert wire['controls']==[[250],[252]] and wire['stopped'] and wire['peak']<32767
    return dict(kick_only_beats=len(kick),snare_beats=len(backbeat),hat=len(hat),crash=len(crash),section_change_seconds=(beats[[16,32]]-beats[0]).tolist(),wire=wire)

if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else d
    result=verify(root)
    (root/'full-mix-analysis.json').write_text(json.dumps(result,indent=2))
    print(result)
