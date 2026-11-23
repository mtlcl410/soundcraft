from copy import deepcopy
from statistics import median
from bench import app, tap, capture, audio, d, np, time, json, save
from assess import matches, mono

RATE = 48000
BPMS = (80, 130, 80)
EDGES = np.cumsum([0] + [16 * 60 / bpm for bpm in BPMS])
source = json.loads((d / 'Back to the Chorus.scraft').read_bytes())

def project(name, parts, role):
    song = deepcopy(source)
    song['name'] = name
    tempos = BPMS if role != 'follow' else (80, 80, 80)
    song['tempo']['tempos'] = [dict(tick=i*15360, bpm=bpm) for i,bpm in enumerate(tempos) if i==0 or bpm!=tempos[i-1]]
    song['markers'] = []
    tracks = []
    for track in song['tracks']:
        part = track['name'].split()[-1].lower()
        if part not in parts:
            continue
        if role != 'song':
            side = -1 if role == 'lead' else 1
            track['mixer']['pan'] = [side,side]
        clip = track['playlists'][0]['clips'][0]
        clip['length'] = round(sum(16*60/b for b in tempos)*RATE)
        seq = clip['content']['Midi']['sequence']
        model = seq['notes'][0]
        events = []
        for b in range(48):
            bar, beat = divmod(b,4)
            if part=='kick':
                events.append((b,60,101 if beat==0 else 89,.22))
            elif part=='hat':
                events += [(b,60,72,.13),(b+.5,60,88,.13)]
            elif part=='snare' and beat in (1,3):
                events.append((b,60,88,.18))
            elif part=='crash' and b in (16,32):
                events.append((b,60,92,1))
            elif part=='bass':
                root=(36,32,39,34)[bar%4]
                events.append((b+.5,root+(12 if 4<=bar<8 and beat%2 else 0),91,.30))
        seq['notes'] = [dict(model,start=round(at*960),pitch=p,velocity=v,length=round(l*960)) for at,p,v,l in events]
        tracks.append(track)
    song['tracks']=tracks
    song['edit']['selected_tracks']=[tracks[0]['id']]
    path=d/(name+'.scraft')
    path.write_text(json.dumps(song),encoding='utf-8')
    return path

def matched(signal, sample):
    scores=matches(signal, mono(d/(sample+'.wav'))[200:1600])
    idx=np.flatnonzero(scores>.85)
    groups=np.split(idx,np.flatnonzero(np.diff(idx)>4800)+1) if len(idx) else []
    return np.array([(g[scores[g].argmax()]-200)/RATE for g in groups])

def run(kind, count):
    music=kind=='mix'
    leader=project(kind+'-leader',('kick','snare') if music else ('kick',),'lead')
    follower=project(kind+'-follower',('bass','hat','crash') if music else ('hat',),'follow')
    with app(follower,kind+'-follower') as follow, app(leader,kind+'-leader') as lead, tap() as wire:
        follow('setup.midi_clock_follow',enabled=True,input='UM-ONE',loss_policy='coast')
        lead('setup.midi_beat_clock',enabled=True,ports={'Model 12 MIDI':{'enabled':True,'offset_samples':0}})
        time.sleep(1.5)
        for i in range(1,count+1):
            name=f'{kind}-{i}'; wire.clear(); states=[]
            with capture(name):
                time.sleep(.3); lead('transport.play',**{'from':0}); start=time.perf_counter()
                while time.perf_counter()-start<EDGES[-1]+.45:
                    states.append([time.perf_counter(),follow('setup.midi_clock_follow')]);time.sleep(.12)
                lead('transport.stop');time.sleep(.85)
            clocks=np.array([t for t,m in wire if m==[248]])
            controls=[m for t,m in wire if m!=[248]]
            bpms=[]
            for a,b in zip(EDGES,EDGES[1:]):
                ts=clocks[(clocks-clocks[0]>a+1.5)&(clocks-clocks[0]<b-1)]
                bpms.append(round(2.5*(len(ts)-1)/(ts[-1]-ts[0]),3))
            xy=audio(name)
            j=dict(bpms=bpms,controls=controls,stopped=not follow('transport.status')['playing'],peak=int(np.max(np.abs(xy))),clocks=len(clocks))
            save(name+'-wire',dict(wire=wire,states=states))
            if not music:
                k=matched(xy[:,0],'Kick');h=matched(xy[:,1],'Hat')
                j.update(kick=k.tolist(),hat=h.tolist())
                if len(k)==48 and len(h)==96:
                    lag=(h[::2]-k)*1000
                    j.update(lag_ms=lag.tolist(),delta_next_beat_ms=[float(lag[idx+1]-median(lag[idx-8:idx-1])) for idx in (16,32)],
                             end_offset_ms=float(median(lag[-4:])-median(lag[6:14])))
            save(name+'-result',j)
            print(name,bpms,j.get('delta_next_beat_ms'),len(j.get('kick',[])),len(j.get('hat',[])),j['stopped'],flush=True)
        lead('setup.midi_beat_clock',enabled=False);follow('setup.midi_clock_follow',enabled=False)

if __name__=='__main__':
    project('EDM 80-130-80',('kick','hat','bass','snare','crash'),'song')
    run('cal',3)
    run('mix',1)
