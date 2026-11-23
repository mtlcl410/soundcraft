from inspect_dips import *
def run(tag):
    p=root/tag;j=read(p/'record.json');b=j['buf'];off=sum(j['anchors'])//2
    start=next(t for t,m in j['events'] if m==[248])+off
    a,h=load_wave(p/'out.bin'),load_wave(p/'in.bin')
    z=read(root/('timing-'+str(b)+'.json'))['long'];aud=read(root/('audio-'+tag+'.json'))
    profile=load_profile(p/'profile.bin')
    outserial=a['serial'].astype(np.int64);inserial=h['serial'].astype(np.int64)
    timingserial=profile[:,0].astype(np.int64)
    result=[]
    for ev in aud['sliding_dips']:
        k=np.searchsorted(outserial,outserial[0]+ev['out_frame']//b)
        m=np.searchsorted(inserial,inserial[0]+ev['in_frame']//b)
        ns=int(a[k]['ns']);ri=np.searchsorted(timingserial,outserial[k]);v=profile[ri-6:ri+7]
        nearest=min([abs(ns-r['ns'])/1e6 for r in z['all']['overruns']],default=None)
        result.append(dict(sample_time_s=ev['time_s'],wall_time_s=(ns-start)/1e9,nearest_overrun_ms=nearest,
                           near_max_callback_ms=float(v[:,2].max())/1e6,near_max_out_arrival_gap_ms=float(np.diff(a[k-6:k+7]['ns'].astype('int64')).max())/1e6,
                           near_max_in_arrival_gap_ms=float(np.diff(h[m-6:m+7]['ns'].astype('int64')).max())/1e6))
    return result
if __name__=='__main__':
    tag=sys.argv[1];q=run(tag);(root/('association-'+tag+'.json')).write_text(json.dumps(q,indent=2));print(q[:6])

