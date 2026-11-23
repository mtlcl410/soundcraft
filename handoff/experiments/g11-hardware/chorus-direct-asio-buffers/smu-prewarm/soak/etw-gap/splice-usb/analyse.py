"""Correlate the observed return splice with callback and duplex USB headers, using recorded data only."""
import json
import sys
from pathlib import Path
from collections import Counter

here = Path(__file__).resolve().parent
base = here.parent
sys.path.insert(0, str(base.parent))
from timing import load_profile, load_wave, np, read, root
from inspect_dips import segment, gain

def headers(path, endpoint_map):
    events = []
    for line in path.read_text().splitlines():
        stamp, kind, fields = line.split('\t', 2)
        if kind not in ('200030', '200031'):
            continue
        d = dict(word.split('=', 1) for word in fields.split() if '=' in word)
        pipe = d['fid_PipeHandle']
        if pipe not in endpoint_map:
            continue
        events.append(dict(t=int(stamp), direction=endpoint_map[pipe], submit=kind=='200030',
            frame=int(d['fid_URB_StartFrame'],16), urb=d['fid_URB_Ptr'], irp=d['fid_IRP_Ptr'],
            n=int(d['fid_UCX_URB_NumberOfPackets'],16), length=int(d['fid_URB_TransferBufferLength'],16),
            status=tuple(int(d[k],16) for k in ('fid_URB_Hdr_Status','fid_URB_ErrorCount','fid_IRP_NtStatus') if k in d)))
    return sorted(events,key=lambda e:e['t'])

def packet_map(tag):
    data = {}
    for line in (here/f'packets-{tag}.txt').read_text().splitlines():
        t, k, pipe, frame, *packets = line.split()
        data[int(t),pipe,int(k),int(frame)] = [tuple(map(int,v.split(':'))) for v in packets]
    return data

def largest(events, ref):
    gap, a, b = max((b['t']-a['t'],a['t'],b['t']) for a,b in zip(events,events[1:]))
    return dict(ms=gap/1e6, start_ms=(a-ref)/1e6, end_ms=(b-ref)/1e6)

def describe(events, packets, pipe, direction, t0):
    lo, hi = t0-5_000_000,t0+12_000_000
    stream=[e for e in events if e['direction']==direction]
    submits={e['frame']:e for e in stream if e['submit']}
    done=[e for e in stream if not e['submit']]
    central=[e for e in done if lo<=e['t']<=hi]
    assert all(b['frame']==a['frame']+1 for a,b in zip(central,central[1:]))
    sizes=Counter()
    scheduled=[]
    counts=[]
    starts=[e for e in stream if e['submit'] and lo<=e['t']<=hi]
    for end in central:
        sub=submits[end['frame']]
        assert (sub['urb'],sub['irp'])==(end['urb'],end['irp']) and sub['t']<end['t']
        assert end['status']==(0,0,0) and end['n']==8 and sub['n']==8
        ps=packets[end['t'],pipe,31,end['frame']]
        ss=packets[sub['t'],pipe,30,sub['frame']]
        assert len(ps)==len(ss)==8 and all(status==0 for _,_,status in ps)
        if direction=='OUT':
            assert sub['length']==end['length'] and [p[0] for p in ss]==[p[0] for p in ps]
            offsets=[p[0] for p in ss]+[sub['length']]
            lengths=[b-a for a,b in zip(offsets,offsets[1:])]
        else:
            lengths=[p[1] for p in ps]
            assert sum(lengths)==end['length']
        sizes.update(lengths)
        scheduled.append((end['t']-sub['t'])/1e6)
        # Count submitted, not yet completed URBs for later frames immediately after each completion.
        counts.append(sum(s['t']<=end['t'] for f,s in submits.items() if f>end['frame']))
    return dict(frames=[central[0]['frame'],central[-1]['frame']],matched=len(central),packets=8*len(central),
        packet_bytes=sizes,completion_error_count=0,pending_after_completion=[min(counts),max(counts)],
        submit_gap=largest(starts,t0),complete_gap=largest(central,t0),
        submit_to_complete_range_ms=[min(scheduled),max(scheduled)])

def frame_info(arr,f,b):
    rec=arr[f//b]
    assert int(rec['serial'])==int(arr[0]['serial'])+f//b
    return dict(frame=f,serial=int(rec['serial']),offset=f%b,ns=int(rec['ns']))

def analyse(tag,b,source):
    d=root/tag
    out,ret=[load_wave(d/f'{name}.bin') for name in ('out','in')]
    prof=load_profile(d/'profile.bin')
    r=read(d/'record.json')
    start=next(t for t,m in r['events'] if m==[248])+sum(r['anchors'])//2
    first_frame=int(np.searchsorted(out['ns'],start))*b
    coarse=read(root/f'audio-{tag}.json')['chunks'][(source-first_frame)//44096]['lag']
    # Determine alignment from independent left and right flanks, outside the test region.
    shifts=[]
    for a in (-1490,600):
        x=segment(out,source+a,850,b)@gain
        y=segment(ret,source+a+coarse-96,850+192,b)
        shifts.append(coarse+int(np.argmin([np.mean((x-y[k:k+850])**2) for k in range(193)]))-96)
    assert shifts[1]-shifts[0]==(40 if b==64 else 0)
    source_block=frame_info(out,source,b)
    t0=source_block['ns']
    capture=frame_info(ret,source+shifts[0],b)
    resume=frame_info(ret,source+shifts[1],b)
    k=source//b
    callbacks=[]
    for j in range(k-2,(source+shifts[1])//b+3):
        serial=int(out[j]['serial'])
        v=prof[np.searchsorted(prof[:,0],serial)]
        assert int(v[0])==serial and int(ret[j]['serial'])==serial and int(ret[j]['size'])==int(out[j]['size'])==b
        def relative(t): return (int(t)-t0)/1e6
        callbacks.append(dict(serial=serial,begin_ms=relative(int(v[1])-int(v[2])),output_ms=relative(out[j]['ns']),
            end_ms=relative(v[1]),work_ms=int(v[2])/1e6,input_ms=relative(ret[j]['ns']),
            reported_input_latency_ms=int(ret[j]['adc'])/1e6))
    meta=read(base/f'usb-evidence-{tag}.json')
    ep={e['pipe']:('OUT' if e['address']=='2' else 'IN') for e in meta['endpoints'] if e['address'] in ('2','81')}
    assert len(ep)==2 and meta['port_path']==[3,4,3]
    events=headers(here/f'native-usb-{tag}.tsv',ep)
    packets=packet_map(tag)
    stats={di:describe(events,packets,pipe,di,t0) for pipe,di in ep.items()}
    # Match the ordered host-controller transfer events to the same endpoint's UCX submits.
    xh=[]
    for line in (here/f'native-usb-{tag}.tsv').read_text().splitlines():
        stamp,kind,fields=line.split('\t',2)
        if kind!='100041':
            continue
        d=dict(word.split('=',1) for word in fields.split() if '=' in word)
        if d.get('fid_SlotId') in meta['xhci_slots'] and d.get('fid_EndpointContextIndex')=='4':
            xh.append((int(stamp),int(d['fid_BytesTotal'],16)))
    submits=[e for e in events if e['submit'] and e['direction']=='OUT']
    host_markers=[]
    for sub,nxt in zip(submits,submits[1:]):
        if t0-5_000_000<=sub['t']<=t0+12_000_000:
            candidates=[t for t,n in xh if sub['t']<=t<nxt['t'] and n==sub['length']]
            assert len(candidates)==1
            host_markers.append(dict(frame=sub['frame'],submit_ms=(sub['t']-t0)/1e6,
                controller_ms=(candidates[0]-t0)/1e6,delta_us=(candidates[0]-sub['t'])/1000))
    stats['OUT']['host_controller']=host_markers
    assert 'EventsLost 0 BuffersLost 0' in (here/f'native-counts-{tag}.txt').read_text()
    assert set(stats['OUT']['packet_bytes'])=={150,180} and set(stats['IN']['packet_bytes'])=={180,216}
    result=dict(source=source_block,main_start=capture,main_resume=resume,main_minus_out_samples=shifts,
        main_witness_since_source_ms=(capture['ns']-t0)/1e6,callbacks=callbacks,usb=stats)
    if b==64:
        inserted=segment(ret,capture['frame'],shifts[1]-shifts[0],b)
        result['return_insert']=dict(nonzero_frames=int(np.any(inserted!=0,axis=1).sum()),
            distinct_per_channel=[len(np.unique(column)) for column in inserted.T],
            min_pcm16=inserted.min(axis=0).tolist(),max_pcm16=inserted.max(axis=0).tolist())
        assert capture['serial']==resume['serial'] and capture['offset']==20 and resume['offset']==60
        assert result['return_insert']['nonzero_frames']==40
        # Use already decoded overrun windows for other late blocks in this take.
        others=headers(base/f'native-usb-{tag}.tsv',ep)
        controls=[]
        for row in read(base/'overruns-usb64r.json')['rows']:
            s=row['serial']; pos=np.searchsorted(prof[:,0],s); origin=int(prof[pos,1])-int(prof[pos,2])
            e=[v for v in others if v['direction']=='OUT' and v['submit'] and abs(v['t']-origin)<=4_000_000]
            assert e[0]['t']<origin-2_000_000 and e[-1]['t']>origin+2_000_000
            controls.append(dict(serial=s, max_submit_gap_ms=largest(e,origin)['ms'],main_shifts=row['audio']['flank_shifts']))
        result['eight_overrun_controls']=controls
    return result

fit=read(base/'overrun-splice.json')
row=next(r for r in read(base/'overruns-usb64r.json')['rows'] if r['serial']==fit['callback'])
offset=fit['fit']['source_boundary_samples_from_callback']
assert fit['control']['source_flank_offsets'][0]==fit['control']['source_flank_offsets'][1]
results={tag:analyse(tag,b,f+offset) for tag,b,f in [
    ('usb64r',64,row['audio']['output_frame']),('usb128',128,fit['control']['ref_frame'])]}
(here/'results.json').write_text(json.dumps(results,indent=2)+'\n')
for tag,result in results.items():
    print(tag,result['main_start'],result['main_resume'],result['main_minus_out_samples'],result['usb'])
print(results['usb64r']['eight_overrun_controls'])
