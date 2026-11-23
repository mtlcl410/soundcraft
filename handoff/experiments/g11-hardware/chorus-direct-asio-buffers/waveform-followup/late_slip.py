from analysis_audio import *
def fit(key,before,after):
 x,y,r=pair(key);pad=64;n=min(len(x),len(y))-pad*2
 cand=lambda sh: x[pad+sh:pad+sh+n]
 y=y[pad:pad+n];a=cand(before);b=cand(after);e0=((a-y)**2).sum(1);e1=((b-y)**2).sum(1);cum=np.r_[0,np.cumsum(e0-e1)];j=int(cum.argmin());pred=np.concatenate([a[:j],b[j:]])
 dy=np.max(abs(np.diff(y-pred,axis=0)),axis=1)
 on=int(np.flatnonzero(abs(a).max(1)>8)[0]);both=np.vstack([a[j-20:j+20],b[j-20:j+20],y[j-20:j+20]])
 return dict(key=key,before=before,after=after,transition_sec_after_music=(j-on)/rate,peak_signal_around_change=float(abs(both).max()),after_piecewise_step_max=float(dy.max()),step_over_16=int((dy>16).sum()),remaining_time_after_music=float((np.argmax(dy)-on)/rate))
results=[fit('repeat-64/late-b',-5,0),fit('panel-64/exact-b',0,6)]
print(results);(d/'offset-change.json').write_text(json.dumps(results,indent=2))

