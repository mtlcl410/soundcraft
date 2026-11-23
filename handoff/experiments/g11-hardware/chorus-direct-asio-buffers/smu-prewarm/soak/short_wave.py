from inspect_dips import run,root,d,read,json,sys
from audio import analyse
def check(size):
    q={}
    for i in range(1,6):
        case='soak-cold'+size+'-'+str(i);p=d/case
        for label in ('exact-a','late-a'):
            tag=case+'/'+label;j=read(p/(label+'.json'))
            meta=dict(buf=int(size),anchors=[a[1] for a in j['anchors']],events=[[round(t*1e9),m] for t,m in j['events']])
            z=analyse(tag,p,meta)
            assert z['counts_8s_pattern']==[int(j['spp']==64)]*2
            dips=[]
            for ev in z['sliding_dips']:
                try:dips.extend(run(tag,p,int(size),dict(sliding_dips=[ev])))
                except AssertionError:dips.append(dict(**ev,unavailable_neighbour=True))
            q[tag]=dict(dips=dips,unavailable_windows=sum(c['windows']-c['valid'] for c in z['chunks']),nonoverlap_dips=z['drop_candidates'])
    return q
if __name__=='__main__':
    size=sys.argv[1];r=check(size);(root/('short-wave-'+size+'.json')).write_text(json.dumps(r,indent=2))
    for k,v in r.items():print(k,'candidates',len(v['dips']),'unknown',v['unavailable_windows'])
