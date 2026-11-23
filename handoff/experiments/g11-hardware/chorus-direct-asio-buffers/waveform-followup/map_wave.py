from analysis_audio import *
loc=read(d/'localize.json');rows=read(src/'metrics.json')
out={}
for key in rows:
 if rows[key]['peak_residual_step']<=16:continue
 x,y,r=pair(key);on=loc[key]['out_onset_frame']-max(0,-r['lag_frames']);bad=loc[key]['flagged_segments'];start=bad[0]['start_aligned_frame']
 # Search 2k frames on both sides, using a 64-frame stereo window and normalized correlation.
 def match(i,n=64):
    u=y[i:i+n];v=x[i-2048:i+2048+n];assert len(v)==4096+n
    corr=sum(np.correlate(v[:,c],u[:,c],mode='valid') for c in range(2))
    v2=np.r_[0,np.cumsum((v*v).sum(1))];err=np.maximum(0,(u*u).sum()+v2[n:]-v2[:-n]-2*corr);k=int(err.argmin())
    return [int(i),k-2048,round(float(np.sqrt(err[k]/(2*n))),2),round(float(np.sqrt((u*u).mean())),2),round(float(np.sqrt(((u-x[i:i+n])**2).mean())),2)]
 near=[match(i) for i in range(start-64,start+1100,32)]
 anchors=[]
 for i in range(on,len(y)-2400,1024):
    if np.sqrt((y[i:i+192]**2).mean())>30:anchors.append(match(i,192))
 out[key]=dict(first_sample_from_start=start-on,start_aligned=start,local=near,anchors=anchors)
 print(key,'first',start-on,'local',[(i-start,k,e) for i,k,e,v,_ in near if v>15][:14],'lags/strong anchors',np.unique([a[1] for a in anchors],return_counts=True))
 if key=='repeat-128/exact-a':print('drop sample',match(51136))
(d/'wave-map.json').write_text(json.dumps(out,indent=2))

