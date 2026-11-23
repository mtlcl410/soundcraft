from timing import *
def summarize(scope):
    findings=[]; intervals=[]
    for i in range(1,6):
        name='soak-cold'+scope+'-'+str(i);p=d/name;a=load_profile(p/'profile.bin');b=int(scope)
        for label in ('exact-a','late-a'):
            j=read(p/(label+'.json'));anchor=sum(z[1] for z in j['anchors'])//2
            start=next(t for t,m in j['events'] if m==[248]);end=next(t for t,m in j['events'] if m==[252])
            lo,hi=np.searchsorted(a[:,1],np.array([start,end])*1e9+anchor);v=a[lo:hi]
            r=report(v,b);findings.extend(dict(take=name+'/'+label,**x) for x in r['overruns'])
            intervals.append(dict(take=name+'/'+label,count=len(v),over=r['over'],max=r['max'],timing_serial_gaps=gaps(v[:,0])))
    return dict(intervals=intervals,overruns=findings)
if __name__=='__main__':
    scope=sys.argv[1];z=summarize(scope);(root/('cold-active-'+scope+'.json')).write_text(json.dumps(z,indent=2))
    print('Boundary takes overruns',len(z['overruns']))

