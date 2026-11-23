"""Attribute the eight in-play overruns, using only the saved 64/128-sample takes."""
from pathlib import Path
from collections import Counter
import bisect
import csv
import json
import sys

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent))
from timing import load_profile, load_wave, read, np, root
from inspect_dips import segment, gain
from audio import sliding_dips

tag = 'usb64r'
case = root / tag
dec = here / ('decoded-' + tag)
b, fs = 64, 44100
tid = read(here / ('partition-' + tag + '.json'))['tid']
assert tid == 13472 and read(dec/'summary.json')['lost'] == 0
focus = {tuple(map(int,line.split())) for line in (here/'windows-usb64r.txt').read_text().splitlines() if line.strip()}

def times(folder):
    meta = read(folder/'record.json')
    offset = sum(meta['anchors'])//2
    return tuple(next(t+offset for t,msg in meta['events'] if msg == [v]) for v in (248,252))

first, stop = times(case)
ref_first, _ = times(root/'usb128')
profile = load_profile(case/'profile.bin').astype(np.int64)
profile = profile[(profile[:,1]>=first)&(profile[:,1]<stop)]
assert len(profile)==372091 and np.all(np.diff(profile[:,0])==1)
hot = profile[profile[:,2]*fs>b*10**9]
assert len(hot)==8
starts = [(int(r[1]-r[2]),int(r[1])) for r in hot]
assert set(starts) <= focus

# Include the preceding transition even if it was outside the selected interval.
transitions = []
for t,c,old,new,state,_ in csv.reader((dec/'switch.csv').open()):
    if int(new)==tid:
        transitions.append((int(t),'run',int(c)))
    elif int(old)==tid:
        transitions.append((int(t),{'Wait':'wait','Ready':'ready','Standby':'ready','DeferredReady':'ready'}.get(state,state),int(c)))
for t,awakened,_,c in csv.reader((dec/'ready.csv').open()):
    if int(awakened)==tid:
        transitions.append((int(t),'ready',int(c)))
transitions.sort(key=lambda x:x[0])
stamps=[r[0] for r in transitions]
interrupts=[]
for t,c,ms,addr,kind in csv.reader((dec/'irq.csv').open()):
    end=int(t)
    interrupts.append((end-round(float(ms)*1e6),end,int(c),kind,addr))

def union(intervals):
    result=[]
    for l,r in sorted(intervals):
        if r<=l: continue
        if result and l<=result[-1][1]:
            result[-1]=(result[-1][0],max(result[-1][1],r))
        else: result.append((l,r))
    return result

def overlap(intervals,lo,hi):
    return sum(max(0,min(r,hi)-max(l,lo)) for l,r in intervals)

def scheduler(lo,hi):
    pos=bisect.bisect_right(stamps,lo)-1
    change=transitions[pos:bisect.bisect_left(stamps,hi)]
    parts=Counter(); off=[]; irq=[]; detail=[]
    for i,(t,state,cpu) in enumerate(change):
        l=max(lo,t); r=change[i+1][0] if i+1<len(change) else hi
        if r<=l: continue
        parts[state]+=r-l
        if state=='run':
            for a,z,c,kind,addr in interrupts:
                if c==cpu and a<r and z>l:
                    near=(max(l,a),min(r,z)); irq.append(near)
                    detail.append(dict(kind=kind,cpu=c,ns=near[1]-near[0],routine=addr))
        else: off.append((l,r))
    assert sum(parts.values())==hi-lo and set(parts)<={'ready','wait','run'}
    windows=union(off+irq)
    return windows,dict(ready_ns=parts['ready'],wait_ns=parts['wait'],on_cpu_irq_union_ns=overlap(union(irq),lo,hi),irq=detail)

def lost_range(windows,earliest,latest,width):
    # An overlap slope can change only when an edge of the translated interval hits an event edge.
    assert earliest<=latest
    points={earliest,latest}
    for interval in windows:
        for x in interval:
            points.update(t for t in (x,x-width) if earliest<=t<=latest)
    values=[overlap(windows,t,t+width) for t in points]
    return min(values),max(values)

digital,main=[load_wave(case/(name+'.bin')) for name in ('out','in')]
ref=load_wave(root/'usb128'/'out.bin')
ref_ns=ref['ns'].astype(np.int64)
audio=read(root/('audio-'+tag+'.json'))
serial0=int(digital[0]['serial'])
play_frame=(int(digital[np.searchsorted(digital['ns'],first)]['serial'])-serial0)*b

def rms(x):return float(np.sqrt(np.mean(x*x)))
def wave_check(frame,t):
    lag=audio['chunks'][(frame-play_frame)//44096]['lag']
    n=2048
    x=segment(digital,frame-n,2*n+b,b)@gain
    y=segment(main,frame+lag-n-96,len(x)+192,b)
    def shift_cost(sh,lo,hi):
        return rms(x[lo:hi]-y[96+sh+lo:96+sh+hi])
    # Align separate leading and trailing flanks; exclude the event and its immediate neighbourhood.
    limits=((-n,-128),(b+128,b+n))
    flanks=[(lo+n,hi+n) for lo,hi in limits]
    shifts=range(-96,97)
    bests=[min(shifts,key=lambda sh:shift_cost(sh,l,r)) for l,r in flanks]
    best=min(shifts,key=lambda sh:sum(shift_cost(sh,l,r)**2 for l,r in flanks))
    y=y[96+best:96+best+len(x)]
    block=x[n:n+b];ret=y[n:n+b]
    # Match a separate 128-sample performance by the musical flanks, keeping the target block held out.
    k=int(np.searchsorted(ref_ns,ref_first+t-first))
    center=(int(ref[k]['serial'])-int(ref[0]['serial']))*128
    radius=6000
    refwave=segment(ref,center-radius-n,2*radius+len(x),128)@gain
    def scores(l,r):
        a=x[l:r];v=refwave[l:2*radius+r]
        cross=sum(np.correlate(v[:,c],a[:,c],'valid') for c in range(2))
        energy=np.r_[0.,np.cumsum((v*v).sum(axis=1))]
        return cross/np.sqrt(np.maximum(energy[r-l:]-energy[:len(cross)],1)*max((a*a).sum(),1))
    ls,rs=(scores(l,r) for l,r in flanks)
    sel=int(np.argmax(ls+rs))
    return dict(output_frame=frame,main_frame=frame+lag+best,flank_shifts=bests,
                expected_rms=rms(block),main_rms=rms(ret),block_error_rms=rms(ret-block),
                block_peak_error=float(np.max(abs(ret-block))),context_error_rms=rms(y-x),
                dip_windows=len(sliding_dips(x,y)),control_zero_detected=bool(sliding_dips(block,np.zeros_like(block))),
                reference128=dict(left_corr=float(ls[sel]),right_corr=float(rs[sel]),
                                  individual_peak_difference=int(np.argmax(ls))-int(np.argmax(rs)),
                                  block_rms_error=rms(refwave[sel+n:sel+n+b]-block)))

results=[]
for row,(lo,hi) in zip(hot,starts):
    serial,_,elapsed,host,flags,render,cmd,packed=map(int,row)
    plugin=packed>>12
    assert packed&4095==b and flags==1 and 0<=plugin<=host<=render<=elapsed
    idx=int(np.searchsorted(digital['serial'],serial)); witness=int(digital[idx]['ns'])
    assert int(digital[idx]['serial'])==serial and lo<=witness<=hi
    unavailable,windows=scheduler(lo,hi);taken=overlap(unavailable,lo,hi)
    # The single process() call is within the callback and ends before the output witness.
    pmin,pmax=lost_range(unavailable,lo,witness-plugin,plugin)
    other=elapsed-plugin
    results.append(dict(serial=serial,elapsed_after_clock_s=(hi-first)/1e9,callback_ns=elapsed,
                        excess_ns=elapsed-b*1e9/fs,plugin_wall_ns=plugin,remaining_wall_ns=other,
                        host_wrapper_exclusive_ns=host-plugin,render_outside_host_ns=render-host,
                        commands_ns=cmd,nonrender_noncommand_ns=elapsed-render-cmd,
                        windows=windows,unavailable_ns=taken,
                        plugin_excluding_unavailable_range_ns=[plugin-pmax,plugin-pmin],
                        other_excluding_unavailable_range_ns=[other-taken+pmin,other-taken+pmax],
                        audio=wave_check((serial-serial0)*b,hi)))
def baseline(v):
    return [round(float(x)) for x in np.percentile(v,[50,95,99])]
all_plugin=profile[:,7]>>12
doc=dict(tid=tid,buffer=b,sample_rate=fs,callback_count=len(profile),threshold_ns=b*1e9/fs,
         baseline_percentiles=[50,95,99],baseline_callback_ns=baseline(profile[:,2]),
         baseline_plugin_ns=baseline(all_plugin),baseline_other_ns=baseline(profile[:,2]-all_plugin),rows=results)
(here/'overruns-usb64r.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
for z in results:
    w=z['windows'];a=z['audio']
    print(z['serial'],round(z['elapsed_after_clock_s'],3),[round(z[k]/1e6,4) for k in ('callback_ns','plugin_wall_ns','remaining_wall_ns','unavailable_ns')],
          [round(w[k]/1e6,4) for k in ('wait_ns','ready_ns','on_cpu_irq_union_ns')],a['flank_shifts'],
          [round(a[k],3) for k in ('expected_rms','main_rms','block_error_rms','context_error_rms','dip_windows')],a['reference128'])

