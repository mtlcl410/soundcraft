"""Compare the calibrated hardware return and digital output throughout the live run."""
import json,sys
from timing import root,d,load_wave,np,rate,read
from pathlib import Path
sys.path.insert(0,str(d.parent/'chorus-direct-asio'))
from assess import mono,matches
template_source=mono(d.parent/'chorus-direct-asio'/'Crash.wav')
template=np.interp(np.arange(round(200*rate/48000),round(2600*rate/48000))*48000/rate,np.arange(len(template_source)),template_source)
metrics=read(d/'metrics.json')
gain=np.median([v['transfer'] for v in metrics.values() if v['peak_residual_step']<4],axis=0)
def flatten(a,b):
    # Keep each callback in its hardware-serial slot, with NaN for missing evidence.
    serial=a['serial'].astype(np.int64)-int(a[0]['serial'])
    assert (np.diff(serial)>0).all() and (a['size']==b).all()
    z=np.full((serial[-1]+1,b,2),np.nan,dtype='f4')
    for i in range(0,len(a),8192):
        z[serial[i:i+8192]]=a['samples'][i:i+8192,:b]*32768
    return z.reshape(-1,2)
def power(a):
    return np.sqrt(np.mean(a*a,axis=(1,2)))
def count_windows(p,y):
    s=power(p);v=power(y);res=power(y-p);valid=np.isfinite(s)&np.isfinite(v)
    return valid,(s>30)&(v<s*.2)&valid,(res>8)&(res>.16*s)&valid
def sliding_dips(p,y):
    # One-sample stride prevents a dead block split across two analysis windows from disappearing.
    def mean_square(z):
        e=(z*z).mean(axis=1);valid=np.isfinite(e)
        prefix=np.r_[0.,np.cumsum(np.where(valid,e,0.),dtype='f8')]
        ct=np.r_[0,np.cumsum(valid)]
        result=np.maximum(0.,(prefix[64:]-prefix[:-64])/64)
        result[(ct[64:]-ct[:-64])<64]=np.nan
        return result
    a=mean_square(p);c=mean_square(y)
    ii=np.flatnonzero((a>30**2)&(c<.04*a))
    if not len(ii): return []
    result=[]
    for g in np.split(ii,np.flatnonzero(np.diff(ii)>64)+1):
        k=int(g[np.argmin(c[g]/a[g])])
        result.append((k,float(a[k]**.5),float(c[k]**.5)))
    return result
def offset(x,y,base):
    # One lag per second. Search near the time-aligned input block. The search
    # uses the entire second, so a missing/repeated 64 samples remains visible.
    n=len(x);pad=3072;l=max(0,base-pad);r=min(len(y),base+n+pad)
    a=np.nan_to_num(x.mean(axis=1));b=np.nan_to_num(y[l:r].mean(axis=1))
    size=1<<(len(a)+len(b)-1).bit_length()
    ab=np.fft.irfft(np.fft.rfft(a[::-1],size)*np.fft.rfft(b,size),size)[n-1:len(b)]
    if not len(ab):raise ValueError((base,l,r))
    u=np.r_[0,np.cumsum(b.astype(float)**2)]
    score=ab/np.sqrt(np.maximum(1,u[n:]-u[:-n])*max(1,np.dot(a,a)))
    i=int(score.argmax());return l+i,float(score[i])
def crash_hits(sig,beg,end):
    # Overlap by the length of the template to cover chunk edges exactly once.
    idx=[]
    for i in range(beg,end,rate*4):
        j=min(end,i+rate*4)
        sc=matches(np.nan_to_num(sig[i:min(len(sig),j+len(template)-1)].mean(axis=1).astype(float)),template)
        hits=np.flatnonzero(sc[:j-i]>.90)
        if len(hits):idx.extend((hits+i).tolist())
    if not idx:return []
    return [int(g[0]) for g in np.split(np.array(idx),np.flatnonzero(np.diff(idx)>rate*.1)+1)]
def longest_muted(y):
    mute=np.max(abs(y),axis=1)<1.1
    edges=np.diff(np.r_[False,mute,False].astype('int8'))
    return max(np.flatnonzero(edges==-1)-np.flatnonzero(edges==1),default=0)
def analyse(tag, folder=None, metadata=None):
    p=folder if folder is not None else root/tag
    j=metadata if metadata is not None else read(p/'record.json');b=j['buf'];anchor=sum(j['anchors'])//2
    ticks=[t+anchor for t,m in j['events'] if m==[248]]
    start=ticks[0];stop=next(t+anchor for t,m in j['events'] if m==[252])
    a=load_wave(p/'out.bin');h=load_wave(p/'in.bin')
    x=flatten(a,b);y=flatten(h,b)
    timestamps={id(arr):arr['ns'].astype(np.int64) for arr in (a,h)}
    output_serials=a['serial'].astype(np.int64)
    def frame(arr,ns):
        i=int(np.searchsorted(timestamps[id(arr)],int(ns)))
        return (int(arr[i]['serial'])-int(arr[0]['serial']))*b
    left=frame(a,start);right=frame(a,stop);width=44096 # multiple of the 64-sample detection window
    chunks=[];dips=[];steps=[];sliding=[];positive=False
    for t in range(left,right,width):
        n=min(width,right-t);xb=x[t:t+n]
        # Timestamp of the actual output block tells us where to look in the independently opened USB input.
        oi=int(np.searchsorted(output_serials,int(a[0]['serial'])+t//b))
        target=frame(h,int(a[oi]['ns']))+t%b
        expected=xb@gain
        iy,score=offset(expected,y,target)
        obs=y[iy:iy+n]
        N=n//64*64
        pp=expected[:N].reshape(-1,64,2); qq=obs[:N].reshape(-1,64,2)
        valid,drop,bad=count_windows(pp,qq)
        rms=power(pp);ir=power(qq);sr=np.max(np.abs(np.diff(obs-expected,axis=0)),axis=1) if n>1 else np.zeros(1)
        if not positive and np.any(rms>100):
            k=np.nanargmax(rms);mock=qq[k:k+1].copy();mock[:]=0
            assert count_windows(pp[k:k+1],mock)[1][0] and sliding_dips(pp[k],mock[0]);positive=True
        # Save every candidate with time and strength for source/return inspection.
        for idx in np.flatnonzero(drop):
            v=int(idx);u=iy+v*64
            dips.append(dict(time_s=(t-left+v*64)/rate,pred_rms=float(rms[v]),obs_rms=float(ir[v]),
                             quiet_samples=int(longest_muted(y[u:u+64])),out_frame=t+v*64,in_frame=u))
        extra=min(63,right-t-n,len(y)-iy-n)
        extended_obs=y[iy:iy+n+extra]
        extended_pred=np.vstack((expected,x[t+n:t+n+extra]@gain)) if extra else expected
        if len(extended_obs)>=64:
            for k,pr,yr in sliding_dips(extended_pred,extended_obs):
                sliding.append(dict(time_s=(t-left+k)/rate,pred_rms=pr,obs_rms=yr,quiet_samples=int(longest_muted(extended_obs[k:k+64])),out_frame=t+k,in_frame=iy+k))
        loc=np.flatnonzero(sr>32)
        if len(loc):
            for g in np.split(loc,np.flatnonzero(np.diff(loc)>256)+1):
                k=int(g[np.argmax(sr[g])]);steps.append([(t-left+k)/rate,float(sr[k])])
        chunks.append(dict(time_s=(t-left)/rate,lag=iy-t,correlation=score,valid=int(valid.sum()),windows=len(valid),
                           bad=int(bad.sum()),dips=int(drop.sum()),peak_residual_step=float(np.nanmax(sr)),
                           output_peak=float(np.nanmax(abs(xb))),main_peak=float(np.nanmax(abs(obs))),
                           clipping=int((abs(obs)>=32767).any(axis=1).sum())))
    assert positive
    # Include the full attack around Stop but exclude the separate startup audio before Continue.
    oh=crash_hits(x,left,right+rate//4); mleft=frame(h,start);mh=crash_hits(y,mleft,frame(h,stop)+rate//4)
    return dict(buf=b,counts_8s_pattern=[len(oh),len(mh)],out_crash_s=[(i-left)/rate for i in oh],
                main_crash_s=[(i-mleft)/rate for i in mh],chunks=chunks,drop_candidates=dips,
                residual_steps=steps,sliding_dips=sliding,calibrated_gain=gain.tolist(),positive_control=positive)
if __name__=='__main__':
    tag=sys.argv[1];z=analyse(tag)
    (root/('audio-'+tag+'.json')).write_text(json.dumps(z,indent=2))
    print(z['counts_8s_pattern'],len(z['drop_candidates']),len(z['residual_steps']),flush=True)
