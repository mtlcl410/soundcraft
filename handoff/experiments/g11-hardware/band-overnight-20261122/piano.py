from bench import *
song=json.loads((hw/'smu-model12-chase.scraft').read_bytes());notes=song['tracks'][0]['playlists'][0]['clips'][0]['content']['Midi']['sequence']['notes']; model=notes[0]
notes[:]=[dict(model,start=int(s*1920),pitch=k) for s,k in [(4.5,60),(5,69),(5.5,78),(7.5,84)]]
file=d/'Piano cue.scraft';file.write_text(json.dumps(song))
def attacks(name):
    x=audio(name).mean(axis=1); e=np.sqrt(np.mean(x[:len(x)//240*240].reshape(-1,240)**2,axis=1))
    idx=np.flatnonzero(e>max(7.,e.max()*.22));groups=np.split(idx,np.flatnonzero(np.diff(idx)>8)+1) if len(idx) else []
    found=[]
    for g in groups:
        a=int(g[0])*240; y=x[a+1200:a+5296]; sp=abs(np.fft.rfft(y*np.hanning(len(y)),16384));hz=np.fft.rfftfreq(16384,1/48000)
        # Identify each target by its fundamental and first three harmonics.
        score={m:sum(sp[abs(hz-(440*2**((m-69)/12))*h)<7].max()/h for h in [1,2,3]) for m in (60,69,78,84)}
        found.append([a/48000,max(score,key=score.get)])
    return found
with app(file,'piano-receiver') as c,output() as send,tap() as wire:
    c('setup.session',frame_rate='30',start_timecode='00:00:00:00')
    c('setup.mtc',input='UM-ONE',online=True,freewheel='none')
    results=[]
    for origin in (0,2,5,5,5):
        name='piano-'+str(len(results));start=len(wire)
        # A distinct parked location makes repeated locate-to-five observable.
        send(full(1));time.sleep(.25);send(full(origin));time.sleep(.4)
        assert c('transport.status')['position']==origin*48000
        with capture(name):
            time.sleep(.25);qfs(send,origin*30,(7-origin)*120);time.sleep(1.2)
        events=attacks(name); stop=c('transport.status');received=wire[start:]
        pitches=[m for _,m in events];gap=next((b[0]-a[0] for a,b in zip(events,events[1:]) if a[1]==69 and b[1]==78),None)
        row=dict(origin=origin,events=events,interval=gap,stopped=not stop['playing'],qf=sum(m[0]==241 for _,m in received))
        row['pass']=pitches==([60,69,78] if origin<5 else [69,78]) and gap is not None and abs(gap-.5)<=.025 and row['stopped'] and row['qf']==(7-origin)*120
        results.append(row);save('piano-results',results);print(name,row,flush=True)
    for mode in ('none','frames','jam_sync'):
        c('setup.mtc',online=True,input='UM-ONE',freewheel=mode,freewheel_frames=8)
        send(full(0));time.sleep(.3);qfs(send,0,240)
        last=time.perf_counter(); rows=[]
        while time.perf_counter()-last<(10.4 if mode=='jam_sync' else .8):
            t=time.perf_counter()-last;rows.append((t,c('transport.status')));time.sleep(.018 if t<.5 else .15)
        gap=time.perf_counter()-last;f=2*30+int(gap*30)//2*2;qfs(send,f,144)
        relock=c('setup.mtc');rolling=c('transport.status');send([252]);time.sleep(.3)
        explicit=not c('transport.status')['playing'];stops=[t for t,s in rows if not s['playing']];end=rows[-1][1]['position']
        ok=(not stops and end>11*48000 if mode=='jam_sync' else bool(stops and (stops[0]<.18 if mode=='none' else .18<stops[0]<.46))) and rolling['playing'] and explicit
        save('freewheel-'+mode,dict(rows=rows,first_stopped=stops[:1],relocked=relock,rolling=rolling,explicit_stop=explicit,passed=ok))
        print('freewheel',mode,stops[:1],rolling['playing'],explicit,ok,flush=True)
    c('setup.mtc',online=False)
    k=len(wire);c('setup.mtc_output',enabled=True,port='Model 12 MIDI',offset_samples=0);time.sleep(.3)
    c('transport.locate',at=384000);time.sleep(.5);a=list(wire[k:]);s1=c('transport.status')
    k=len(wire);c('transport.play',**{'from':384000});time.sleep(2.2);c('transport.stop');time.sleep(.3);b=list(wire[k:])
    k=len(wire);c('transport.locate',at=576000);time.sleep(.5);z=list(wire[k:]);s2=c('transport.status')
    ff=lambda r:[m for _,m in r if m[:5]==[240,127,127,1,1]]
    vals=[m[1] for _,m in b if m[0]==241];groups=[]
    for i in range(len(vals)-7):
        g=vals[i:i+8]
        if [v>>4 for v in g]==list(range(8)):groups.append((g[2]&15)*30+(g[3]&3)*16*30+(g[0]&15)+16*(g[1]&1))
    ok=ff(a)[-1:]==[full(8)] and ff(z)[-1:]==[full(12)] and len(groups)>20 and all(y-x==2 for x,y in zip(groups,groups[1:])) and not s1['playing'] and not s2['playing']
    save('lighting-cues',dict(before=ff(a),after=ff(z),groups=groups,stopped=[s1,s2],passed=ok,raw=a+b+z));print('lighting',ok,len(groups),flush=True)
    c('setup.mtc_output',enabled=False)
