from analysis_audio import *
rows=read(src/'metrics.json');res={}
for key,r in rows.items():
 x,y,_=pair(key);p=src/key;j=read(p.with_suffix('.json'));b=r['size'];lag=r['lag_frames'];ev=j['events'];t0=next(t for t,m in ev if m==[248]);out=np.array(j['out']['ns'])/1e9;ins=np.array(j['in']['ns'])/1e9;dx=np.diff(out)*1000;di=np.diff(ins)*1000
 loud=np.flatnonzero(np.abs(x).max(1)>8)[0];err=y-x;step=np.max(abs(np.diff(err,axis=0)),axis=1)
 bad=np.flatnonzero(step>16);groups=np.split(bad,np.flatnonzero(np.diff(bad)>512)+1) if len(bad) else []
 # Look for late callbacks near the start of the first large transient; count since last callback; does not identify execution time.
 k=(int(loud)+max(0,-lag))//b
 def gaps(arr,st,en):return [round(float(t),3) for t in arr[max(0,st):en]]
 near=dx[k-4:k+6]
 obj={'size':b,'out_onset_frame':int(loud)+max(-lag,0),'main_alignment_lag':lag,'max_out_gap_near_onset_ms':float(max(near)),'nominal_ms':b*1000/rate,'out_gaps_ms':gaps(dx,k-4,k+6),'max_step_fixed_gain':float(step.max()),'flagged_segments':[]}
 for g in groups:
    start=int(g[0]);end=int(g[-1])+1;idx=(start+max(-lag,0))//b;ii=(start+max(lag,0))//b
    obj['flagged_segments'].append({'start_aligned_frame':start,'end_aligned_frame':end,'ms_from_first_music':round((start-loud)*1000/rate,3),'output_near_ms':gaps(dx,idx-3,idx+4),'input_near_ms':gaps(di,ii-3,ii+4)})
 res[key]=obj
 if r['peak_residual_step']>16 or key.endswith('256/exact-b'): print(key,'lag',lag,'first music',loud,'from first ms',obj['flagged_segments'][0]['ms_from_first_music'] if groups else '-', 'gaps near start',obj['out_gaps_ms'],'step',round(step.max(),1))
(d/'localize.json').write_text(json.dumps(res,indent=2))

