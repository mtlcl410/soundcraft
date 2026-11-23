from analysis_audio import *
from quality import quality
from pathlib import Path
import argparse
def calc(case):
 records=[];p=src/case
 a=np.fromfile(p/'profile.bin',dtype='<u8').reshape(-1,8)
 for f in sorted(p.glob('*-out.wav')):
    name=f.name[:-8];j=read(p/(name+'.json'));buf=j['out']['size'];ev=j['events'];first=next(t for t,m in ev if m==[248])
    offset=(j['anchors'][0][1]+j['anchors'][1][1])//2
    stamps=np.array(j['out']['ns'])+offset
    ix=np.searchsorted(a[:,1].astype('int64'),stamps)
    ok=ix<len(a); valid=ix[ok];diff=a[valid,1].astype('int64')-stamps[ok]
    assert abs(np.median(diff))<100000 and np.all(diff>=0)
    x=stereo(f);y=stereo(f.with_name(name+'-in.wav'));v=quality(x,y);lag=v['lag_frames'];xs=x[max(0,-lag):];ys=y[max(0,lag):];n=min(len(xs),len(ys));pred=xs[:n]@np.array(v['transfer']);err=ys[:n]-pred
    onset=int(np.flatnonzero(abs(x).max(1)>12)[0]);k=onset//buf;block=a[ix[k]]
    info=lambda row:[round(float(row[i])/1e6,4) for i in (2,5,3,6)]+[int(row[4]) & 255]
    cb=a[valid];scope=(stamps[ok]-offset)/1e9;cb=cb[(scope>=first-.02)&(scope<=ev[-1][0]+.06)]
    lat=(block[1].astype('int64')-offset)/1e9-first
    o=dict(take=name,block_size=buf,rms_drop=v['drop_windows'],peak_residual_step=float(abs(np.diff(err,axis=0)).max()),first_nonzero_block=info(block),worst_block=info(cb[cb[:,2].argmax()]),nearby=[info(a[z]) for z in ix[k-2:k+3]],first_clock_to_out_ms=round(lat*1000,3))
    records.append(o);print(case,name,'first [fill/mix/VST/drain/n]',o['first_nonzero_block'],'worst',o['worst_block'],'step',round(o['peak_residual_step'],1))
 (d/(case+'-summary.json')).write_text(json.dumps(records,indent=2))
if __name__=='__main__':
 for name in sys.argv[1:]:calc(name)

