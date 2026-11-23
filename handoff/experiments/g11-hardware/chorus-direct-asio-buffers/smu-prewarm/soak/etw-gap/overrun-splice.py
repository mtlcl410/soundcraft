"""Validate the shift at callback 37505 against independent musical and hardware references."""
from pathlib import Path
import sys,json
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/'dip486'))
from splice import fit
from original import align,segment,root,gain,load_wave,read,np,rms

def take(tag):
    p=root/tag
    r=read(p/'record.json')
    t=next(t for t,m in r['events'] if m==[248])+sum(r['anchors'])//2
    return load_wave(p/'out.bin'),load_wave(p/'in.bin'),t

out,main,start=take('usb64r')
ref,ret,ref_start=take('usb128')
r=next(row for row in read(here/'overruns-usb64r.json')['rows'] if row['serial']==37505)
frame=r['audio']['output_frame']
def frame_at(w,t,b):return (int(w[np.searchsorted(w['ns'],t)]['serial'])-int(w[0]['serial']))*b
def rough_lag(tag,w,t,frame,b):
    return read(root/f'audio-{tag}.json')['chunks'][(frame-frame_at(w,t,b))//44096]['lag']
def best_flanks(x,y,radius):
    def pick(l,h):
        errs=[rms(x[l:h]-y[radius+s+l:radius+s+h]) for s in range(-radius,radius+1)]
        return int(np.argmin(errs))-radius
    return (pick(0,896),pick(len(x)-896,len(x)))
n=1536
delta=rough_lag('usb64r',out,start,frame,64)
x=segment(out,frame-n,2*n,64)@gain
m=segment(main,frame+delta-n-96,len(x)+192,64)
pre,post=best_flanks(x,m,96)
assert post-pre==40
# With the prefix aligned, MAIN inserts (post-pre) samples at the fitted source boundary.
y=segment(main,frame+delta+pre-n,2*n,64)
xf=segment(out,frame-n-(post-pre),len(y)+post-pre,64)@gain
f=fit(xf,y,post-pre);i=f['index'];insert=y[i:i+post-pre]
boundary=i-n
f.update(source_boundary_samples_from_callback=boundary,insert_time_ms=1000*(post-pre)/44100,
         inserted_peak=float(np.max(abs(insert))),constant_alignment_pre_rms=rms(y-x),
         constant_alignment_post_rms=rms(y-xf[:len(y)]),before_main_shift=pre,after_main_shift=post,
         exact_callback_residual_after_realignment=rms(segment(out,frame,64,64)@gain-segment(main,frame+delta+post,64,64)) if boundary<=0 else None)
# The two halves of the independent control must select the same alignment.
t=int(out[np.searchsorted(out['serial'],r['serial'])]['ns'])
center=frame_at(ref,ref_start+(t-start),128)
radius=8000; refsig=segment(ref,center-radius-n,2*radius+len(x),128)@gain
offsets=[align(refsig,x[l:h])[0]-l for l,h in [(0,896),(len(x)-896,len(x))]]
assert abs(offsets[0]-offsets[1])<=1
ref_frame=center-radius+offsets[0]
rx=segment(ref,ref_frame-n,2*n,128)@gain
lag=rough_lag('usb128',ref,ref_start,ref_frame,128)
ry=segment(ret,ref_frame-n+lag-96,len(rx)+192,128)
rs=best_flanks(rx,ry,96)
v=ry[96+rs[0]:96+rs[0]+len(rx)]
control=dict(ref_frame=ref_frame,source_flank_offsets=offsets,pre_main_shift=rs[0],post_main_shift=rs[1],
             digital_64_vs_128_rms=rms(rx-x),main_128_vs_output_128_rms=rms(v-rx),
             source_boundary_64_block=(frame+boundary)//64+int(out[0]['serial']))
doc=dict(callback=r['serial'],fit=f,control=control)
# Positive and negative controls use the same quiet digital passage.
synthetic=np.vstack((x[:i],np.zeros((post-pre,2)),x[i:]))[:len(y)]
positive=fit(xf,synthetic,post-pre)
assert positive['index']==i and positive['flank_rms']<1e-8
no_insert=segment(out,frame-n-96,len(x)+192,64)@gain
assert best_flanks(x,no_insert,96)==(0,0)
doc['synthetic_controls']=dict(no_insert_shifts=[0,0],insert_samples=post-pre,recovered_boundary=positive['index']-n)
# Independent window widths should locate the same splice at the same source sample.
sensitivity=[]
for width in (768,1024,2048):
  fx=segment(out,frame-width-(post-pre),2*width+post-pre,64)@gain
  fy=segment(main,frame+delta+pre-width,2*width,64)
  test=fit(fx,fy,post-pre)
  sensitivity.append(test['index']-width)
assert sensitivity==[boundary]*3 and rs[0]==rs[1]
doc['window_checks_samples_from_callback']=sensitivity

print(json.dumps(doc,indent=2));(here/'overrun-splice.json').write_text(json.dumps(doc,indent=2)+'\n')


