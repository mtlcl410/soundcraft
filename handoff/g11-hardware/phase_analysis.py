"""Compare render, WASAPI packet and loopback callback timestamps for the same sample."""
from desktop_sync import root
import sys, json, struct, wave
sys.path.insert(0,str(root/'capture-deps'))
import numpy as np
rate=48000
def records(path):
    with path.open('rb') as f:
        while header:=f.read(40):
            cb,dev,utc,pos,seq,n=struct.unpack('<QQQdII',header)
            yield cb,dev,utc,pos,seq,np.frombuffer(f.read(4*n),'<f4')
class Tap:
    def __init__(self,rows,offset):
        self.rows=rows
        self.seq=[r[4] for r in rows]
        self.gaps=int(sum(b!=a+1 for a,b in zip(self.seq,self.seq[1:])))
        self.starts=np.cumsum([0]+[len(r[-1]) for r in rows])
        self.y=np.concatenate([r[-1] for r in rows]).astype(float)
        self.cb=np.array([(r[2]-offset)/1e9 for r in rows])
        self.dev=np.array([r[1]/1e9 for r in rows])
        self.pos=np.array([r[3] for r in rows])
    def time(self,i,clocks):
        k=int(np.searchsorted(self.starts,i,side='right')-1)
        return clocks[k]+(i-self.starts[k])/rate
def align(template,y,estimate,margin=9000):
    lo=max(0,estimate-margin);hi=min(len(y),estimate+margin+len(template))
    cut=y[lo:hi]
    prod=np.correlate(cut,template)
    sums=np.r_[0.,np.cumsum(cut*cut)]
    energy=np.maximum(sums[len(template):]-sums[:-len(template)],1e-16)
    quality=prod/np.sqrt(energy*np.dot(template,template))
    k=int(np.argmax(quality))
    return lo+k,float(quality[k])
def run(base,render):
    d=json.loads((root/(base+'.json')).read_text())
    off=d['wall_qpc_offset_ns']
    r=Tap([x for x in records(root/render) if d['started']-.6<(x[2]-off)/1e9<d['ended']+.3],off)
    n=Tap(list(records(root/(base+'-native.bin'))),off)
    ps=np.cumsum([0]+[b[1] for b in d['blocks']])
    pe=np.array([b[0] for b in d['blocks']])
    with wave.open(str(root/(base+'.wav')),'rb') as w:
        py=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,w.getnchannels()).mean(axis=1)
    def pyt(i):
        k=np.searchsorted(ps,i,side='right')-1
        return pe[k]+(i-ps[k+1])/rate
    wire=json.loads((root/(base+'-wire.json')).read_text())
    group=[];m=[];t=[]
    for stamp,port,b in wire:
        if not port.startswith('UM-ONE') or b[0]!=241: continue
        k=b[1]>>4
        if k==0: group=[]
        if len(group)!=k: continue
        group.append(b[1]&15)
        if k==7:
            fr,s,mi,h=[group[j]+16*group[j+1] for j in range(0,8,2)]
            assert h>>5==3
            m.append((h&31)*3600+mi*60+s+(fr+2)/30);t.append(stamp)
    if m: assert np.allclose(np.diff(m),2/30)
    nfft=2048;hop=480
    freq=np.array([abs(np.fft.rfft(py[i:i+nfft]*np.hanning(nfft),8192))[12:820] for i in range(0,len(py)-nfft,hop)])
    energy=np.sqrt(np.mean(freq**2,axis=1))
    score=np.maximum(0,energy-np.r_[np.repeat(energy[0],4),energy[:-4]])
    peaks=[j for j in range(12,len(score)-12) if score[j]>max(30,.045*score.max()) and score[j]==max(score[j-12:j+13])]
    detected=[(pyt(int(j*hop+1024)),int(round(69+12*np.log2(np.median([12+row.argmax() for row in freq[j:j+8]])*rate/8192/440)))) for j in peaks]
    notes=[]
    for sec in [5,5.5]+list(range(6,32)):
        target=sec*rate
        if target>=r.pos[-1]-rate*.12: break
        k=int(np.searchsorted(r.pos,target,side='right'))
        lo=r.pos[k-1] if k else 240000
        if not (lo<=target<r.pos[k]):continue
        slot=int(r.starts[k]+round((target-lo)*len(r.rows[k][-1])/(r.pos[k]-lo)))
        # First sustained 1-ms RMS window over 5% of the first 120-ms peak.
        anchor=max(0,slot-600); y=r.y[anchor:slot+5760]
        env=np.sqrt(np.convolve(y*y,np.ones(48)/48,mode='valid'))
        attack=anchor+int(np.flatnonzero(env>env.max()*.05)[0])+24
        st=r.time(slot,r.cb); rt=r.time(attack,r.cb)
        tmp=r.y[attack:attack+2400]
        guess=int(n.starts[min(len(n.dev)-1,np.searchsorted(n.dev,rt))])
        ni,cn=align(tmp,n.y,guess)
        guess=int(ps[min(len(pe)-1,np.searchsorted(pe,rt))])
        pi,cp=align(tmp,py,guess)
        nt=n.time(ni,n.dev);pt=pyt(pi)
        legacy,pitch=min(detected,key=lambda p:abs(p[0]-pt))
        assert cn>.93 and cp>.93 and abs(legacy-pt)<.12,(sec,cn,cp)
        expected_time=float(np.interp(sec,m,t)) if m and m[0]<=sec<=m[-1] else None
        ms=lambda v:round(1000*v,3)
        notes.append(dict(sec=sec,pitch=pitch,render_attack_qpc=rt,render_slot_qpc=st,
            threshold_clear_at_window_start=bool(env[0]<=env.max()*.05),
            endpoint_delay_ms=ms(nt-expected_time) if expected_time else None,
            chase=ms(st-expected_time) if expected_time else None,attack=ms(rt-st),output=ms(nt-rt),
            delivery=ms(pt-nt),detector=ms(legacy-pt),total=ms(legacy-expected_time) if expected_time else None,
            native_corr=round(cn,5),py_corr=round(cp,5)))
    result=dict(base=base,render=render,notes=notes,detected=detected,wire_frames=len(m),last_external=m[-1] if m else None,
        last_wire_qpc=t[-1] if t else None,stop_qpc=d['ended'],after_stop_capture=round(pe[-1]-d['ended'],3),
        render_gaps=r.gaps,native_gaps=n.gaps,matching_total=len(notes),all_pitches=[p for _,p in detected],
        buffer_sizes=sorted(set(len(v[-1]) for v in r.rows)),first_interval=round(detected[1][0]-detected[0][0],4))
    (root/(base+'-breakdown.json')).write_text(json.dumps(result,indent=2))
    print(base,'gaps',r.gaps,n.gaps,'qfs',len(m),'first',result['first_interval'],'notes',result['all_pitches'])
    for row in notes:
        if row['sec']>=17: print(row)
if __name__=='__main__':
    run(sys.argv[1],sys.argv[2])

