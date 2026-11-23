"""Recheck low-level candidates using local waveform matches on both sides."""
from timing import *
from audio import gain
def segment(a,f,n,b):
    serial=int(a[0]['serial'])+f//b
    lo=f//b
    if lo>=len(a) or a[lo]['serial']!=serial:
        lo=np.searchsorted(a['serial'],serial)
    rec=a[lo:lo+(f%b+n+b-1)//b]
    assert rec[0]['serial']==serial and gaps(rec['serial'])==0
    return rec['samples'][:,:b].reshape(-1,2)[f%b:f%b+n].astype(float)*32768
def local(x,y,k,n):
    # Window in MAIN at k; choose delay in +/-384 samples that minimizes
    # absolute squared error to calibrated ASIO. Form the stereo sum of squared errors.
    k+=1200
    a=y[k:k+n];v=x[k-384:k+384+n]
    corr=sum(np.correlate(v[:,c],a[:,c],'valid') for c in range(2))
    vs=np.r_[0.,np.cumsum((v*v).sum(1))]; e=np.maximum(0,(a*a).sum()+vs[n:]-vs[:-n]-2*corr)
    pick=int(e.argmin());return dict(rms=float(np.sqrt((a*a).mean())),lag=int(pick-384),error=float(np.sqrt(e[pick]/(2*n))))
def run(tag, folder=None, buf=None, waveform=None):
    p=folder if folder is not None else root/tag
    b=buf if buf is not None else read(p/'record.json')['buf'];z=waveform if waveform is not None else read(root/('audio-'+tag+'.json'))
    a,h=load_wave(p/'out.bin'),load_wave(p/'in.bin');result=[]
    for v in z['sliding_dips']:
        x=segment(a,v['out_frame']-1200,3000,b)@gain;y=segment(h,v['in_frame']-1200,3000,b)
        anchors=[dict(offset=k,**local(x,y,k,n)) for k,n in [(-512,192),(-256,128),(-128,128),(0,64),(64,128),(192,192),(384,384),(768,256)]]
        best=local(x,y,-256,576)
        offsets=[h['lag'] for h in anchors if h['offset']!=0 and h['rms']>=10 and h['error']<max(5,h['rms']*.12)]
        candidates=sorted(set([0,best['lag']]+offsets));tests=[]
        for shift in candidates:
            pred=x[1200+shift:1264+shift];obs=y[1200:1264]
            tests.append(dict(shift=shift,pred_rms=float(np.sqrt((pred**2).mean())),obs_rms=float(np.sqrt((obs**2).mean())),err=float(np.sqrt(((pred-obs)**2).mean()))))
        result.append(dict(**v,anchors=anchors,full_neighbourhood=best,neighbour_offsets=tests))
    return result
if __name__=='__main__':
    tag=sys.argv[1];r=run(tag);(root/('dips-'+tag+'.json')).write_text(json.dumps(r,indent=2))
    for z in r:
        print(round(z['time_s'],3),[(a['offset'],round(a['rms'],2),a['lag'],round(a['error'],2)) for a in z['anchors']],z['full_neighbourhood'])
