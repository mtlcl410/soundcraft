"""Relate the original return dip to callback work, inter-callback gaps and the matching 128-sample passage."""
from pathlib import Path
import sys,json
here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parent))
from inspect_dips import root,read,np,rate,segment,load_wave,load_profile,gain,local
from audio import matches
def align(a,z):
    sc=matches(a.mean(1),z.mean(1));i=int(sc.argmax());return i,float(sc[i])
def rms(x):return float(np.sqrt((x*x).mean()))
def extract(b,e=None):
    p=root/f'long{b}';j=read(p/'record.json')
    a,h=[load_wave(p/(k+'.bin')) for k in ['out','in']];prof=load_profile(p/'profile.bin')
    t0=next(t for t,m in j['events'] if m==[248])+sum(j['anchors'])//2
    def ftime(arr,ns):
        i=np.searchsorted(arr['ns'].astype('int64'),ns);return int(arr[i]['serial']-arr[0]['serial'])*b
    if b==64:
        v=next(v for v in read(root/'dips-long64.json') if v['quiet_samples']==64);f,g=v['out_frame'],v['in_frame'];match=1
    else:
        center=ftime(a,t0+int(486.24e9));prior=center-9000
        sig=segment(a,prior,18500,b)
        idx,match=align(sig,e);f=prior+idx+64
        # Independent waveform landmarks anchor the same musical attack across separate performances.
        landmarks=[align(sig,e[lo:hi])[0]-lo for lo,hi in ((0,128),(128,384),(384,640))]
        assert max(abs(i-idx) for i in landmarks)<=3,landmarks
        k=f//b;pk=ftime(h,int(a[k]['ns']))-3072
        ref=segment(a,f-64,640,b)@gain
        off,score=align(segment(h,pk,8000,b),ref);g=pk+off+64
        assert score>.95,score
    x=segment(a,f-1200,3000,b)@gain;y=segment(h,g-1200,3000,b)
    ip=np.searchsorted(prof[:,0],int(a[0]['serial'])+f//b);v=prof[ip-12:ip+13].astype('int64')
    end=v[:,1];cost=v[:,2];entry=end-cost
    # Align independent streams by wall clock for the trace; keep their signal positions separately.
    ai=f//b;hi=np.searchsorted(h['ns'].astype('int64'),int(a[ai]['ns']));waveg=g//b
    rows=[]
    for i in range(1,len(v)):
        ih=hi+i-12;ow=ai+i-12
        rows.append(dict(block=i-12,serial=int(v[i,0]),start_ms=(entry[i]-entry[12])/1e6,work_ms=cost[i]/1e6,
                         entry_delta_ms=(entry[i]-entry[i-1])/1e6,outside_ms=(entry[i]-end[i-1])/1e6,input_delta_ms=(int(h[ih]['ns'])-int(h[ih-1]['ns']))/1e6,
                         output_stamp_ms=(int(a[ow]['ns'])-int(a[ow-1]['ns']))/1e6))
    inds=np.flatnonzero((abs(y)<=1.1).all(axis=1))
    runs=[z for z in np.split(inds,np.flatnonzero(np.diff(inds)>1)+1) if len(z) and z[0]<=1200<=z[-1]]
    anchor=[dict(frame=k,**local(x,y,k,n)) for k,n in [(-512,192),(-256,128),(-128,128),(0,64),(64,128),(192,192),(384,384)]]
    return dict(buf=b,output_frame=f,input_frame=g,match_to_64=match,out_rms=rms(x[1200:1264]),in_rms=rms(y[1200:1264]),reference_rms=rms(x[1200:1264]),quiet_run=[int(runs[0][0])-1200,len(runs[0])] if runs else None,
                anchors=anchor,rows=rows,input_dip_block_vs_host=int(waveg-hi),
                input_signal_phase=g%b,output_signal_phase=f%b,
                window_gaps=[int((np.diff(w['serial'][q-20:q+20])!=1).sum()) for w,q in [(a,ai),(h,waveg)]]),segment(a,f-64,640,b)
if __name__=='__main__':
    r,z=extract(64);s,_=extract(128,z);(here/'original.json').write_text(json.dumps([r,s],indent=2))
    for v in (r,s):
        print(v['buf'],v['out_rms'],v['in_rms'],v['quiet_run'],v['match_to_64'])
        print(sorted(v['rows'],key=lambda x:-x['entry_delta_ms'])[:3])

