from pathlib import Path
import json,subprocess,sys,time
here=Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent),str(here.parent/'capture-deps')]
import rtmidi
from desktop_sync import cmd,rpc
from assess import mono,matches,np
src=here.parent/'band-tempo-1669-clip-fix'
subprocess.run([sys.executable,str(here/'launch.py')],cwd=here,check=True)
p=json.loads((here/'control.json').read_bytes())['port']
try:
    for nm in ('exact-final','panel-first','tempo-b','tempo-120'):
        cue=nm in ('exact-final','panel-first')
        src=here.parent/('band-chorus-live-20261122' if cue else 'band-tempo-1669-clip-fix')
        original=json.loads((src/(nm+'.json')).read_bytes())['midi']
        msgs=[(t,m) for t,n,m in original if n.startswith('UM-ONE')]
        start=next(i for i,(t,m) in enumerate(msgs) if m[0] in (250,251))
        end=next(i for i,(t,m) in enumerate(msgs[start:],start) if m[0]==252)
        replay=msgs[start:end+1]
        with subprocess.Popen([sys.executable,'-u',str(here/'take_live.py'),nm],cwd=here,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True) as rec:
            ready=rec.stdout.readline();print(ready,flush=True);assert 'READY' in ready
            output=rtmidi.MidiOut()
            port,=[i for i,n in enumerate(output.get_ports()) if n.rsplit(' ',1)[0]=='Model 12 MIDI']
            output.open_port(port)
            try:
                pointer=next((m for _,m in reversed(msgs[:start]) if m[0]==242),[242,0,0]); output.send_message(pointer);time.sleep(1.45)
                wall=time.perf_counter()
                for t,m in replay:
                    time.sleep(max(0,wall+(t-replay[0][0])-time.perf_counter()))
                    output.send_message(m)
            finally:
                output.close_port()
            print(rec.communicate(timeout=12)[0],flush=True);assert rec.returncode==0
        cap=json.loads((here/(nm+'.json')).read_bytes())
        received=[m for t,n,m in cap['midi'] if n.startswith('UM-ONE') and m[0] in (248,250,251,252)]
        assert received==[m for _,m in replay]
        x=mono(here/(nm+'.wav'))
        scores={}
        for label in ('Snare','Hat','Crash'):
            c=matches(x,mono(here/(label+'.wav'))[200:2100]);hits=np.flatnonzero(c>.78)
            g=np.split(hits,np.flatnonzero(np.diff(hits)>4800)+1) if len(hits) else []
            scores[label]=[round((int(h[c[h].argmax()])-200)/48000,5) for h in g]
        exp=32*60/(100 if nm=='tempo-b' else 120)
        if cue:
            expected_spp=64 if nm=='exact-final' else 65
            assert pointer==[242,expected_spp,0] and any(t['position']==expected_spp*6000 and not t['playing'] for _,t,_ in cap['states'])
            assert len(scores['Crash'])==int(expected_spp==64) and len(scores['Snare'])>=2,scores
            assert not cap['states'][-1][1]['playing']
            result=dict(spp=expected_spp,crash=len(scores['Crash']),snares=len(scores['Snare']),clocks=sum(m[0]==248 for m in received),stopped=True)
            (here/(nm+'-result.json')).write_text(json.dumps(result,indent=2));print(result,flush=True)
            continue
        assert len(scores['Snare'])==8 and len(scores['Crash'])==1,scores
        assert abs(scores['Hat'][-1]-scores['Crash'][0]-15.5*exp/32)<.05
        result=dict(take=nm,pulses=sum(m[0]==248 for m in received),crash=len(scores['Crash']),snares=len(scores['Snare']),last_hat_after_crash=scores['Hat'][-1]-scores['Crash'][0],clip_seconds=exp,stopped=not cap['states'][-1][1]['playing'])
        assert result['stopped']
        (here/(nm+'-result.json')).write_text(json.dumps(result,indent=2));print(result,flush=True)
finally:
    cmd(p,'setup.midi_clock_follow',enabled=False);rpc(p,'app.quit',{})
