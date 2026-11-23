"""Associate real DIN time labels with both actual ASIO channels, using unique source markers."""
import csv,json,sys,wave
from pathlib import Path
hw=Path(__file__).resolve().parent
sys.path.insert(0,str(hw/'audio'))
from m1 import np,read_blocks
def source_samples():
    with wave.open(str(hw/'audio/manual-stimulus/chase-135s.wav')) as w:
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768.
def analyse(f,rate='30'):
    sys.path.insert(0,str(hw/'midi'))
    from wire_source import RATES
    num,den,code=RATES[rate]
    nominal=round(num/den)
    segments=json.loads((f/'segments.json').read_text())
    with (f/'wire.csv').open() as w:
        packets=[(int(r['qpc_ns']),bytes.fromhex(r['hex'])[1]) for r in csv.DictReader(w) if r['hex'].startswith('f1')]
    meta,pcm,b=read_blocks(f/'driver')
    sr=int(meta['sample_rate']);n=meta['buffer'];freq=meta['qpc_frequency']
    block_seconds=b['qpc'].astype(float)/freq
    def timestamp(i):
        return block_seconds[i//n]+(i%n)/sr
    src=source_samples()
    out=[]
    for s in segments:
        rows=[r for r in packets if s['first']<=r[0]<=s['last']]
        groups=[]
        for k in range(len(rows)-7):
            d=[v for _,v in rows[k:k+8]]
            if [v>>4 for v in d]!=list(range(8)):continue
            d=[v&15 for v in d]
            assert d[7]>>1==code,(d[7],rate)
            minutes=(d[6]+16*(d[7]&1))*60+d[4]+16*d[5]
            frame=(minutes*60+d[2]+16*d[3])*nominal+d[0]+16*d[1]
            if code==2:frame-=2*(minutes-minutes//10)
            groups.append((rows[k][0]/1e9,frame))
        if not groups:continue
        origin=float(np.median([stamp-frame*den/num for stamp,frame in groups]))
        first=groups[0][1]*den/num;last=groups[-1][1]*den/num
        markers=[]
        for half in range(270):
            at=.25+half*.5
            if not first<=at<=last:continue
            near=origin+at
            ix=int(np.searchsorted(block_seconds,near))
            if not 1<=ix<len(b): continue
            center=(ix-1)*n+round((near-block_seconds[ix-1])*sr)
            lo=max(0,center-int(.24*sr));hi=min(len(pcm),center+int(.24*sr))
            template=src[round(at*sr):round(at*sr)+127]
            if hi-lo<=len(template):continue
            matches=[]
            for c in (0,1):
                sig=pcm[lo:hi,c].astype(float)
                cc=np.correlate(sig,template,'valid')
                j=int(np.argmax(abs(cc)));peak=sig[j:j+len(template)]
                score=float(abs(cc[j])/max(1e-12,np.linalg.norm(template)*np.linalg.norm(peak)))
                matches.append(dict(index=lo+j,score=round(score,6),ms=round((timestamp(lo+j)-near)*1000,4)))
            markers.append(dict(t=at,tx=matches[0],rx=matches[1]))
        out.append(dict(first_frame=groups[0][1],last_frame=groups[-1][1],qfs=len(rows),origin_qpc_s=origin,markers=markers))
    (f/'marker-phase.json').write_text(json.dumps(out,indent=2))
    for r in out:
        valid=[m for m in r['markers'] if min(m['tx']['score'],m['rx']['score'])>=.85]
        print(r['first_frame'],r['qfs'],len(valid),'/',len(r['markers']),'first',valid[:1])
    return out
if __name__=='__main__':analyse(Path(sys.argv[1]))

