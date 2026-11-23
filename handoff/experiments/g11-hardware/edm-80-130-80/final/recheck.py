from bench import *
from statistics import median
import threading
original=json.loads((d/'Back to the Chorus.scraft').read_bytes())
def score(label,track,step,side,bpms):
    j=json.loads(json.dumps(original));t=next(t for t in j['tracks'] if t['name']==track);j['tracks']=[t];t['mixer']['pan']=[side,side]
    # A short, repeated note allows independent transient counting on the two stems.
    clip=t['playlists'][0]['clips'][0];notes=clip['content']['Midi']['sequence']['notes'];note=notes[0]
    notes[:]=[dict(note,start=tick,pitch=60 if side<0 else 60,length=144) for tick in range(0,30720,step)]
    j['tempo']['tempos']=[dict(tick=tick,bpm=bpm) for tick,bpm in bpms]
    clip['length']=round(sum(16*60/b for _,b in bpms)*48000) if len(bpms)==2 else round(32*60/bpms[0][1]*48000)
    f=d/(label+'.scraft');f.write_text(json.dumps(j));return f
def hits(x, label):
    from assess import mono, matches
    box=matches(x,mono(d/(label+'.wav'))[200:1600])
    idx=np.flatnonzero(box>.85)
    groups=np.split(idx,np.flatnonzero(np.diff(idx)>4800)+1) if len(idx) else []
    return np.array([(g[box[g].argmax()]-200)/48000 for g in groups])
def trial(bpm1,bpm2):
    label=f'fixed-calibrated-{bpm1}-{bpm2}';f=score(label+'-drums','S-MU2000 Kick',960,-1,[(0,bpm1),(15360,bpm2)])
    g=score(label+'-keys','S-MU2000 Hat',480,1,[(0,120)])
    with app(g,label+'-follower') as rec,app(f,label+'-leader') as lead,tap() as wire:
        rec('setup.midi_clock_follow',enabled=True,input='UM-ONE',loss_policy='coast')
        lead('setup.midi_beat_clock',enabled=True,ports={'Model 12 MIDI':{'enabled':True,'offset_samples':0}})
        time.sleep(.65)
        for segment,beat0 in [('top',0)]:
            name=label+'-'+segment;wire.clear();states=[]
            with capture(name):
                time.sleep(.25);start=time.perf_counter();origin=round(beat0*60/bpm1*48000);lead('transport.play',**{'from':origin})
                dur=(16-beat0)*60/bpm1+16*60/bpm2
                while time.perf_counter()-start<dur+.45:
                    states.append((time.perf_counter(),rec('transport.status'),rec('setup.midi_clock_follow')));time.sleep(.14)
                lead('transport.stop');time.sleep(.65)
            xy=audio(name);drums=hits(xy[:,0],'Kick');keys=hits(xy[:,1],'Hat');stopped=not rec('transport.status')['playing']
            controls=[m for _,m in wire if m[0]!=248];ts=np.array([t for t,m in wire if m[0]==248])
            def bpm(t0,t1):
                seg=ts[(ts-ts[0]>t0)&(ts-ts[0]<t1)]
                return round(60*(len(seg)-1)/(24*(seg[-1]-seg[0])),3) if len(seg)>2 else None
            wire_bpm=[bpm(1,3),bpm(dur-3,dur-1)]
            same_count=len(drums)==32-beat0 and len(keys)==2*len(drums)
            lag=1000*(keys[::2]-drums) if same_count else []
            ctrl=([[250],[252]] if not beat0 else [[242,64,0],[251],[252]])
            checks=dict(drums=len(drums)==32-beat0,keys=len(keys)==(32-beat0)*2,tempo=all(abs(x-y)<1 for x,y in zip(wire_bpm,[bpm2 if beat0 else bpm1,bpm2])),transport=controls==ctrl,stop=stopped,
                alignment=same_count and max(abs(lag))<60,drift=same_count and abs(median(lag[-4:])-median(lag[:4]))<30)
            result=dict(passed=bool(all(checks.values())),checks={k:bool(v) for k,v in checks.items()},controls=controls,bpm=wire_bpm,drums=drums.tolist(),keys=keys.tolist(),lag_ms=list(lag),states=states,raw=list(wire))
            save(name+'-results',result);print(name,checks,len(drums),len(keys),wire_bpm,controls,flush=True)
        lead('setup.midi_beat_clock',enabled=False);rec('setup.midi_clock_follow',enabled=False)
for a,b in ((120,100),(100,120)):trial(a,b)
