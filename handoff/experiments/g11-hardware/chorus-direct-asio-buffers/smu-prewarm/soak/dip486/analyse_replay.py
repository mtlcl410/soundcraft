from original import *
def estimate(y,x,t,start,n):
    # Relative to the submitted sample coordinate; stereo transfer already calibrated.
    lo=-128;hi=2048
    off,score=align(y[t+start+lo:t+start+n+hi],x[16384+start:16384+start+n])
    return off+lo,score
def run(b):
    z=np.load(here/f'replay-{b}.npz');c=z['calls'];raw=z['source'];x=raw.astype(float)*32768@gain;y=z['recording'].astype(float)*32768
    records=[]
    for t,hold in zip(z['targets'],z['held']):
        t=int(t);k=np.flatnonzero(c[:,0]==t)[0]
        pre,psc=estimate(y,x,t,-1800,768);post,qsc=estimate(y,x,t,1200,900)
        assert min(psc,qsc)>.96,(psc,qsc)
        j=np.arange(-1200,1200);observed=y[t+post+j]
        contiguous=(np.max(abs(observed),axis=1)<=1.1)
        edges=np.diff(np.r_[False,contiguous,False].astype('int8'));runs=[]
        for i,end in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
            if end-i<20:continue
            l=int(j[i]);r=int(j[end-1])+1;n=r-l
            # Find adjacent source samples using the 128 return samples on either side.
            ly=t+l+post;ry=t+r+post
            def local_match(iy,dry_start):
                cand=x[16384+dry_start-512:16384+dry_start+512+128]
                u=y[iy:iy+128];co=sum(np.correlate(cand[:,ch],u[:,ch],'valid') for ch in range(2))
                vs=np.r_[0,np.cumsum((cand*cand).sum(1))];cost=np.maximum(0,(u*u).sum()+vs[128:]-vs[:-128]-2*co)
                h=int(cost.argmin());return dry_start-512+h,np.sqrt(cost[h]/256),rms(u)
            ii,ei,si=local_match(ly-128,l-128);oo,eo,so=local_match(ry,r)
            runs.append(dict(offset=l,len=n,rms=rms(y[ly:ry]),before_error=ei,after_error=eo,before_rms=si,after_rms=so,next_source_gap=oo-(ii+128)))
        iy=t+post
        flags=c[k-12:k+13,5]
        records.append(dict(held=bool(hold),ready_interval_ms=(c[k,3]-c[k-1,3])/1e6,delay_inside_ms=(c[k,3]-c[k,2])/1e6,actual_cb_gap_ms=float(np.diff(c[k-6:k+7,2]).max())/1e6,
                         pre_lag=pre,post_lag=post,pre_corr=psc,post_corr=qsc,target_expected_rms=rms(x[16384:16448]),target_observed_rms=rms(y[iy:iy+64]),target_error_rms=rms(x[16384:16448]-y[iy:iy+64]),quiet_runs=runs,flags=int(np.bitwise_or.reduce(flags))))
    return records
if __name__=='__main__':
    for b in map(int,sys.argv[1:]):
        r=run(b);(here/f'independent-{b}.json').write_text(json.dumps(r,indent=2))
        for v in r:print(b,v['held'],v['pre_lag'],v['post_lag'],round(v['ready_interval_ms'],2),round(v['target_error_rms'],2),[(q['offset'],q['len'],q['next_source_gap']) for q in v['quiet_runs']])

