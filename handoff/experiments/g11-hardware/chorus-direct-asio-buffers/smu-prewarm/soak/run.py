"""Exercise a single uninterrupted physical MIDI Clock stream and ASIO playback."""
from pathlib import Path
import sys,json,os,shutil,time,subprocess,hashlib,copy
root=Path(__file__).resolve().parent
d=root.parent.parent
audit=d.parent
sys.path[:0]=[str(audit),str(audit/'capture-deps')]
import numpy as np, rtmidi
from desktop_sync import cmd
buf=int(sys.argv[1]); seconds=int(sys.argv[2]); tag=sys.argv[3]
base=audit/'chorus-direct-asio'
src=base/'session'
lib=root.parent/'validated-plugins'
case=root/tag; case.mkdir()
session=root/'session'
def sha(p):
    with p.open('rb') as h: return hashlib.file_digest(h,'sha256').hexdigest()
song='Back to the Chorus.scraft'
assert sha(src/song)=='992c9ea2e252052261f326a03be545683f3bf9a59d1db5ab166a0acc1d5a7071'
if not session.exists():
    shutil.copytree(src,session)
    data=json.loads((src/song).read_bytes())
    for tr in data['tracks']:
        clips=tr['playlists'][0]['clips']
        assert len(clips)==1 and clips[0]['start']==0 and clips[0]['length']==16*48000
        for i in range(1,40):
            clip=copy.deepcopy(clips[0]);clip['start']=i*16*48000
            clip['id']=data['next_id'];data['next_id']+=1
            clips.append(clip)
    (session/song).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
assert 8+seconds<640
os.environ.update(SC_PROF=str(case/'profile.bin'),SC_ASIO_WITNESS=str(case/'in.bin'),SC_OUTPUT_WITNESS=str(case/'out.bin'),PYTHONUTF8='1')
s=(base/'launch.py').read_text().replace('str(here.parent)',repr(str(audit))).replace("old=here/'session'","old=pathlib.Path("+repr(str(session))+")").replace("exe=here/'soundcraft.exe'","exe=pathlib.Path("+repr(str(d/'waveform-followup'/'soundcraft.exe'))+")").replace('E:/S-MU2000-windows-x64/plugins',lib.as_posix()).replace('buffer_size=256','buffer_size='+str(buf))
(case/'launch.py').write_text(s)
def anchor():
    vals=[]
    for _ in range(40):
        a=time.perf_counter_ns();v=time.time_ns();b=time.perf_counter_ns();vals.append((b-a,v-(a+b)//2))
    return min(vals)[1]
mout=rtmidi.MidiOut();mi=rtmidi.MidiIn();events=[];states=[]
try:
    with (case/'launch.log').open('w') as h:subprocess.run([sys.executable,'launch.py'],cwd=case,stdout=h,stderr=subprocess.STDOUT,timeout=75,check=True)
    ctl=json.loads((case/'control.json').read_bytes());port=ctl['port']
    assert ctl['sha256']=='74f10eb6d56230847c3aaaab57aa92f7c88391e09e33d27ac767b45081d2e3de'
    ps=f"(Get-Process -Id {ctl['pid']}).Modules | Where-Object ModuleName -like '*MU2000*' | Select-Object -ExpandProperty FileName"
    mods=subprocess.check_output(['powershell','-NoProfile','-Command',ps],text=True).strip().splitlines()
    assert len(mods)==1 and Path(mods[0]).resolve().is_relative_to(lib) and sha(Path(mods[0]))=='61019edbf714036ac4d43d7a7192d9b521d3810b49bd7efa02e7fec852a52737',mods
    for key in ('out','in'):
        with (case/(key+'.bin')).open('rb') as h: header=np.fromfile(h,'<u8',4)
        assert header[3]==buf,(key,header)
    mi.ignore_types(sysex=True,timing=False,active_sense=True)
    mi.open_port(next(i for i,n in enumerate(mi.get_ports()) if n.startswith('UM-ONE')))
    def capture(ev,_):
        if ev[0][0] in (242,248,251,252):events.append([time.perf_counter_ns(),ev[0]])
    mi.set_callback(capture)
    ids=[i for i,n in enumerate(mout.get_ports()) if n.rsplit(' ',1)[0]=='Model 12 MIDI' or n=='Model 12 MIDI']
    assert len(ids)==1;mout.open_port(ids[0])
    a=anchor();mout.send_message([242,64,0]);time.sleep(.5)
    status=cmd(port,'transport.status');assert status['position']==384000 and not status['playing'],status
    mout.send_message([251]);t=time.perf_counter()
    for tick in range(seconds*48):
        time.sleep(max(0,t+tick/48-time.perf_counter()));mout.send_message([248])
        if tick%1440==600:
            status=cmd(port,'transport.status');states.append([tick,status])
            print(tick//48,status['position'],status['playing'],flush=True)
    mout.send_message([252]);time.sleep(1);b=anchor()
    final=cmd(port,'transport.status')
    (case/'record.json').write_text(json.dumps(dict(events=events,anchors=[a,b],states=states,final=final,buf=buf,seconds=seconds,dll_sha256=sha(Path(mods[0])),dll=mods[0])))
    assert len([1 for _,m in events if m[0]==248])==seconds*48 and [m for _,m in events if m[0]!=248]==[[242,64,0],[251],[252]]
    assert not final['playing'] and all(x['playing'] for _,x in states)
finally:
    if mout.is_port_open() and not (case/'record.json').exists():mout.send_message([252])
    if mi.is_port_open():mi.cancel_callback();mi.close_port()
    if mout.is_port_open():mout.close_port()
    if (case/'control.json').exists():
        try:cmd(json.loads((case/'control.json').read_bytes())['port'],'app.quit')
        except OSError:pass


