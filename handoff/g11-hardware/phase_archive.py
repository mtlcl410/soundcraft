"""Re-score the archived physical take with the same wave-envelope rule used for the paired tests."""
from phase_analysis import *
base='smu-interval-fixed-1795132844773399100'
d=json.loads((root/(base+'.json')).read_text())
summary=json.loads((root/(base+'-analysis.json')).read_text())
with wave.open(str(root/(base+'.wav')),'rb') as w:
    y=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,w.getnchannels()).mean(axis=1)
pe=np.array([b[0] for b in d['blocks']])
cs=np.cumsum([0]+[b[1] for b in d['blocks']])
def stamp(index):
    k=np.searchsorted(cs,index,side='right')-1
    return pe[k]+(index-cs[k+1])/rate
wire=json.loads((root/(base+'-wire.json')).read_text())
g=[]; mt=[]; qt=[]
for t,port,b in wire:
    if not port.startswith('UM-ONE') or b[0]!=241: continue
    k=b[1]>>4
    if k==0:g=[]
    assert k==len(g)
    g.append(b[1]&15)
    if k==7:
        fr,s,mi,h=[g[i]+16*g[i+1] for i in range(0,8,2)]
        assert h>>5==3
        mt.append((h&31)*3600+mi*60+s+(fr+2)/30)
        qt.append(t)
assert np.allclose(np.diff(mt),2/30)
rows=[]
for item,obs in zip(summary['notes_against_compensated_mtc'],summary['onsets']):
    sec=item['expected_s']
    if sec<17:continue
    old=d['started']+obs[0]
    i=np.searchsorted(pe,old)
    center=int(cs[i+1]+(old-pe[i])*rate)
    lo=center-3600; cut=y[lo:center+4800]
    env=np.sqrt(np.convolve(cut*cut,np.ones(48)/48,mode='valid'))
    audio=stamp(lo+int(np.flatnonzero(env>env.max()*.05)[0])+24)
    target=float(np.interp(sec,mt,qt))
    rows.append(dict(s=sec,wave_delay_ms=round((audio-target)*1000,2),old_fft_delay_ms=round((old-target)*1000,2),detector_difference_ms=round((old-audio)*1000,2)))
print(rows)
(root/(base+'-wave-timing.json')).write_text(json.dumps(rows,indent=2))

