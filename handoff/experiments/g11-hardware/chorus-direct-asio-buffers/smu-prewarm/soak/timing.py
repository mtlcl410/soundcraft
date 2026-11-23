from pathlib import Path
import sys,json
root=Path(__file__).resolve().parent
d=root.parent.parent
sys.path[:0]=[str(d),str(d/'waveform-followup')]
from analysis_audio import np,stereo,read

dtype=np.dtype([('ns','<u8'),('adc','<u8'),('serial','<u8'),('size','<u8'),('samples','<f4',(256,2))])
rate=44100
def load_wave(p):
    assert p.stat().st_size%dtype.itemsize==0
    return np.memmap(p,mode='r',dtype=dtype)
def load_profile(p):
    data=np.fromfile(p,'<u8');return data[:len(data)//8*8].reshape(-1,8)
def gaps(x):
    return int(np.maximum(0,np.diff(x.astype('int64'))-1).sum())
def report(v,buf):
    t=v[:,2].astype(float)/1e6;deadline=1000*buf/rate
    hot=t>deadline
    streaks=np.diff(np.r_[False,hot,False].astype('int8'))
    ids=np.flatnonzero(hot)
    def row(i):
        r=[int(n) for n in v[i]]
        return dict(serial=r[0],ns=r[1],relative_seconds=round((r[1]-int(v[0,1]))/1e9,5),
                    measured_ms=r[2]/1e6,host_ms=r[3]/1e6,foreign_ms=(r[7]>>12)/1e6,render_ms=r[5]/1e6,commands_ms=r[6]/1e6)
    return dict(count=len(v),first=row(0),max=row(t.argmax()),min_headroom_ms=deadline-t.max(),
                percentiles_ms=dict(zip(['p50','p95','p99','p99.9','p99.99'],np.percentile(t,[50,95,99,99.9,99.99]))),
                near_005ms=int(((t<=deadline)&(t>=deadline-.005)).sum()),over=len(ids),overruns=[row(i) for i in ids],
                bursts=int((streaks==1).sum()),longest_streak=int(max(np.flatnonzero(streaks==-1)-np.flatnonzero(streaks==1),default=0)))
def match_profile(a,ns,serial):
    i=np.searchsorted(a[:,0],serial)
    assert i<len(a) and a[i,0]==serial and 0<=int(a[i,1])-int(ns)<5_000_000,(a[i,0],serial)
    return i
def cold(tag):
    p=d/tag;a=load_profile(p/'profile.bin');out=load_wave(p/'out.bin');r={}
    for label in ['exact-a','late-a']:
        j=read(p/(label+'.json'));buf=j['out']['size'];assert r or label=='exact-a'
        k=int(np.flatnonzero(np.max(abs(stereo(p/(label+'-out.wav'))),axis=1)>12)[0])//buf
        t=j['out']['ns'][k]+sum(x[1] for x in j['anchors'])//2
        i=np.searchsorted(out['ns'],t);assert int(out[i]['ns'])==t
        q=match_profile(a,t,out[i]['serial'])
        r[label]=report(a[q:q+1],buf)['first']
    return r
def long(tag):
    p=root/tag;j=read(p/'record.json');buf=j['buf'];a=load_profile(p/'profile.bin')
    out=load_wave(p/'out.bin');ins=load_wave(p/'in.bin')
    an=sum(j['anchors'])//2
    ticks=[t+an for t,m in j['events'] if m==[248]]
    stop=next(t+an for t,m in j['events'] if m==[252])
    lo,hi=np.searchsorted(a[:,1],[ticks[0],stop]);v=a[lo:hi]
    assert (v[:,7]&4095==buf).all() and gaps(v[:,0])==0
    q=np.searchsorted(out['ns'],ticks[0])
    k=int(np.flatnonzero(abs(out[q:q+1000]['samples'][:,:buf]).max(axis=(1,2))>12/32768)[0])+q
    first=match_profile(a,out[k]['ns'],out[k]['serial'])
    assert int(a[first,4])&255
    z=dict(buf=buf,deadline_ms=1000*buf/rate,ticks=len(ticks),duration_s=(stop-ticks[0])/1e9,
          wall_anchor_delta_ms=(j['anchors'][1]-j['anchors'][0])/1e6,
          first_music=report(a[first:first+1],buf)['first'],all=report(v,buf),after_first=report(a[first+1:hi],buf),
          foreign_calls=int((v[:,4]&255).sum()),serial_gaps_profile=gaps(v[:,0]),end=j['final'])
    for key,arr in [('in',ins),('out',out)]:
        start,end=np.searchsorted(arr['ns'],[ticks[0],stop])
        block=arr[start:end]
        z[key]=dict(gaps=gaps(block['serial']),count=len(block),sizes=np.unique(block['size']).tolist())
    return z
if __name__=='__main__':
    tag=sys.argv[1]
    z=long('long'+tag)
    cs={k:cold(k) for k in ['soak-cold'+tag+'-'+str(i) for i in range(1,6)]}
    (root/('timing-'+tag+'.json')).write_text(json.dumps(dict(long=z,cold=cs),indent=2))
    print(z['all']['count'],z['all']['over'],z['all']['max'],flush=True)

