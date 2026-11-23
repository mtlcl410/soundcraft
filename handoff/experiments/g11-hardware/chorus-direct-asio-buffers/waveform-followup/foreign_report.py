from analysis_audio import *
out={}
for case in sys.argv[1:]:
 p=src/case;a=np.fromfile(p/'profile.bin','<u8').reshape(-1,8);recs=[]
 for f in sorted(p.glob('*-out.wav')):
    name=f.name[:-8];j=read(p/(name+'.json'));b=j['out']['size'];z=stereo(f);k=int(np.flatnonzero(abs(z).max(1)>12)[0])//b
    t=j['out']['ns'][k]+(j['anchors'][0][1]+j['anchors'][1][1])//2;i=np.searchsorted(a[:,1],t);v=[int(n) for n in a[i]]
    assert v[1]>=t and v[1]-t<2_000_000 and v[7]&4095==b
    r={'take':name,'block':b,'total_ms':v[2]/1e6,'host_vst_call_ms':v[3]/1e6,'plugin_calls':v[4]&255,'setProcessing_ms':(v[4]>>8)/1e6,'mix_ms':v[5]/1e6,'command_drain_ms':v[6]/1e6,'foreign_process_ms':(v[7]>>12)/1e6}
    recs.append(r);print(case,name,'total/host_vst/set/process/drain',*(round(r[s],3) for s in ('total_ms','host_vst_call_ms','setProcessing_ms','foreign_process_ms','command_drain_ms')))
 out[case]=recs
(d/'foreign-calls.json').write_text(json.dumps(out,indent=2))

