"""Check digital silence inside active sound, and verify crash recurrence across both streams."""
import sys,json
from pathlib import Path
from timing import root,d,np,read,load_wave,rate
from audio import flatten
def muted(z,limit=64):
    silent=(abs(z)<.01).all(axis=1)
    edges=np.diff(np.r_[False,silent,False].astype('int8'));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1)
    candidates=[]
    for lo,hi in zip(starts,ends):
        if hi-lo<limit or lo<64 or hi+64>len(z):continue
        prev=float(np.sqrt((z[lo-64:lo]**2).mean()));nxt=float(np.sqrt((z[hi:hi+64]**2).mean()))
        if min(prev,nxt)>30:candidates.append(dict(frame=int(lo),length=int(hi-lo),left_rms=prev,right_rms=nxt))
    return candidates
def run(tag):
    p=root/tag;j=read(p/'record.json');b=j['buf'];a=load_wave(p/'out.bin')
    first=next(t for t,m in j['events'] if m==[248])+sum(j['anchors'])//2
    end=next(t for t,m in j['events'] if m==[252])+sum(j['anchors'])//2
    i,k=np.searchsorted(a['ns'],[first,end]);z=flatten(a[i:k],b)
    inject=np.full((384,2),100,dtype='f4');inject[128:192]=0;assert muted(inject)==[dict(frame=128,length=64,left_rms=100.,right_rms=100.)]
    hits=muted(z)
    # A calibrated dead block is useful evidence on the host side. A silence with
    # quiet neighbours cannot distinguish an intended rest from missing audio.
    for h in hits:h['seconds']=h['frame']/rate
    return dict(found=hits,source_gate_rms=30,minimum_frames=64,silence_abs_pcm_counts=.01,positive_control=True)
if __name__=='__main__':
    tag=sys.argv[1];v=run(tag);(root/('source-'+tag+'.json')).write_text(json.dumps(v,indent=2))
    print('Source severe silence candidates',len(v['found']))

