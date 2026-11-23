"""Locate S-MU2000 attacks on the native WASAPI sample clock and compare to the physical MTC input."""
from phase_analysis import Tap, records, root, rate, np
import sys,json,wave

def spectral_events(y):
    size=2048; hop=480
    spec=np.array([abs(np.fft.rfft(y[j:j+size]*np.hanning(size),8192))[12:820] for j in range(0,len(y)-size,hop)])
    level=np.sqrt(np.mean(spec**2,axis=1))
    rise=np.maximum(0,level-np.r_[np.repeat(level[0],4),level[:-4]])
    peaks=[j for j in range(12,len(rise)-12) if rise[j]>max(30,.045*rise.max()) and rise[j]==max(rise[j-12:j+13])]
    def semitone(j):
        bins=[]
        for spectrum in spec[j:j+8]:
            k=int(spectrum.argmax())
            assert 0<k<len(spectrum)-1
            left,middle,right=np.log(np.maximum(spectrum[k-1:k+2],1e-20))
            bins.append(12+k+0.5*(left-right)/(left-2*middle+right))
        return float(69+12*np.log2(np.median(bins)*rate/8192/440))
    return [(j*hop+size//2,semitone(j)) for j in peaks]

def measure(base):
    d=json.loads((root/(base+'.json')).read_text())
    n=Tap(list(records(root/(base+'-native.bin'))),d['wall_qpc_offset_ns'])
    assert n.gaps==0 and all(b[2]==0 for b in d['blocks'])
    ref=base.startswith('smu-phase-reference')
    wire=json.loads((root/(base+'-wire.json')).read_text())
    mt=[];qt=[];raw=[];group=[]
    for t,port,b in wire:
        if not port.startswith('UM-ONE') or b[0]!=241:continue
        raw.append(t)
        k=b[1]>>4
        if k==0:group=[]
        assert k==len(group)
        group.append(b[1]&15)
        if k==7:
            frames,sec,mi,h=[group[i]+16*group[i+1] for i in (0,2,4,6)]
            assert h>>5==3
            mt.append((h&31)*3600+mi*60+sec+(frames+2)/30);qt.append(t)
    if not ref:
        assert qt and np.allclose(np.diff(mt),2/30)
        assert any(ch['status']=='Located' and tr['position']==240000 and not tr['playing'] for _,ch,tr in d['states'])
    with wave.open(str(root/(base+'.wav')),'rb') as w:
        pcm=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,w.getnchannels()).mean(axis=1)
    edges=np.cumsum([0]+[b[1] for b in d['blocks']])
    def pyt(i):
        k=np.searchsorted(edges,i,side='right')-1
        return d['blocks'][k][0]+(i-edges[k+1])/rate
    old=spectral_events(pcm)
    found=spectral_events(n.y*32768)
    assert len(found)==len(old) and all(abs(p-q)<.1 for (_,p),(_,q) in zip(found,old))
    expected=[(5,69),(5.5,78)]+[(i,[65,71,67,73][(i-6)%4]) for i in range(6,32)]
    notes=[]
    for (idx,pitch),(sec,expect) in zip(found,expected):
        assert abs(pitch-expect)<.75,(sec,expect,pitch) # includes the 3% exploratory take
        # 1ms RMS / 5% of attack peak. Restrict the three closely spaced opening notes to their fundamentals
        # to reject the previous note's release. Use the same rule on the local control.
        lo=idx-int(.11*rate); segment=n.y[lo:idx+int(.11*rate)]
        if sec<=6:
            size=1440
            tone=np.exp(-2j*np.pi*(440*2**((pitch-69)/12))*np.arange(size)/rate)*np.hanning(size)
            envelope=abs(np.convolve(segment,tone,'valid'))
        else:
            size=48
            envelope=np.sqrt(np.convolve(segment**2,np.ones(size)/size,'valid'))
        assert envelope[0]<.05*envelope.max(),(sec,idx)
        frame=lo+int(np.flatnonzero(envelope>.05*envelope.max())[0])+size//2
        attack=n.time(frame,n.dev)
        late_ms=round(1000*(attack-np.interp(sec,mt,qt)),2) if mt and mt[0]<=sec<=mt[-1] else None
        notes.append(dict(score_seconds=sec,expected_pitch=expect,measured_semitone=round(pitch,3),cents_from_note=round(100*(pitch-expect),1),qpc=attack,delay_ms=late_ms))
    assert len(notes)==len(found)
    res=dict(take=base,raw_qf=len(raw),wire_end=mt[-1] if mt else None,
      first_interval_frequency_s=round(notes[1]['qpc']-notes[0]['qpc'],5),
      first_interval_legacy_s=round(pyt(old[1][0])-pyt(old[0][0]),5),notes=notes,
      post_wire_notes=sum(bool(x['qpc']>raw[-1]) for x in notes) if raw else None,
      post_stop_capture_s=round(d['blocks'][-1][0]-d['ended'],3))
    (root/(base+'-acquisition.json')).write_text(json.dumps(res,indent=2))
    print(base,res['first_interval_frequency_s'],res['first_interval_legacy_s'],len(notes),res['wire_end'],[(r['score_seconds'],r['delay_ms']) for r in notes if 14<=r['score_seconds']])
if __name__=='__main__':
    for arg in sys.argv[1:]:measure(arg)

