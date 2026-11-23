"""Isolated SoundCraft desktop, physical DIN input, and ASIO input/output in the same QPC domain."""
import contextlib, csv, json, os, queue, socket, subprocess, sys, time
from pathlib import Path
hw = Path(__file__).resolve().parent
sys.path[:0] = [str(hw/'audio'), str(hw/'midi')]
from m1_app import apply, cmd
from m1 import read_blocks
from midi_path import live_midi
from wire_source import source, mtc

def save(p, obj):
    p.write_text(json.dumps(obj, indent=2), 'utf8')

@contextlib.contextmanager
def desktop(folder, wav, buffer_frames=256, sample_rate=48000, project=None):
    # Each run records the binary actually launched, including locally integrated builds.
    from hashlib import sha256
    manifest = Path(os.environ.get('SC_ACCEPTANCE_BUILD', hw/'audio/build/f561a57a-build.json'))
    build = json.loads(manifest.read_text('utf-8-sig'))
    exe = Path(build['exe'])
    with exe.open('rb') as binary:
        digest = sha256()
        while data := binary.read(1024*1024):
            digest.update(data)
    if digest.hexdigest() != build['sha256']:
        raise ValueError(f'Executable differs from {manifest}')
    save(folder/'build.json', build)
    driver = folder/'driver'
    driver.mkdir()
    cfg = folder/'private-settings'
    cfg.mkdir()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = os.environ | dict(SOUNDCRAFT_NO_PREFS='1', SOUNDCRAFT_CONFIG_DIR=str(cfg), SC_ASIO_EVIDENCE=str(driver), SC_ASIO_RETURN_INDEX='8')
    if project:
        env.update(VST3_PATH='E:/S-MU2000-windows-x64/plugins', CLAP_PATH='E:/S-MU2000-windows-x64/plugins', S_MU2000_ROMS='E:/S-MU2000-windows-x64/roms')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    with (folder/'application.log').open('xb') as log:
        proc = subprocess.Popen([exe,'--control',str(port)], cwd=folder, env=env, stdout=log, stderr=log, startupinfo=startup)
        try:
            for _ in range(180):
                if proc.poll() is not None: raise RuntimeError('Desktop exited')
                try:
                    cmd(port,'transport.status')
                    break
                except OSError: time.sleep(.25)
            else: raise TimeoutError('Control socket')
            if project:
                cmd(port,'file.open',path=str(project))
            else:
                cmd(port,'session.new',name='Model 12 hardware session',sample_rate=sample_rate)
            save(folder/'session-setup.json',cmd(port,'setup.session',start_timecode='00:00:00:00',frame_rate='30'))
            if wav:
                cmd(port,'file.import_audio',path=str(wav),new_tracks=True,at=0)
            track=cmd(port,'track.new',kind='audio',name='Silent capture')['tracks'][0]
            cmd(port,'mix.mute',tracks=[track],value=True)
            cmd(port,'ui.audio_device',system='ASIO',input='Model Mixer ASIO',output='Model Mixer ASIO',sample_rate=sample_rate,buffer_size=buffer_frames)
            cmd(port,'mix.record_arm',tracks=[track],value=True)
            for _ in range(70):
                if list(driver.glob('epoch-*.bin')) and max(p.stat().st_size for p in driver.glob('epoch-*.bin'))>262144: break
                time.sleep(.15)
            else: raise RuntimeError('No live duplex PCM')
            epoch=max(driver.glob('epoch-*.json'),key=lambda p:p.stat().st_mtime_ns)
            meta=json.loads(epoch.read_text())
            assert meta['buffer']==buffer_frames and meta['sample_rate']==sample_rate and meta['input_index']==8, meta
            device=dict(device='Model Mixer ASIO',sample_rate=meta['sample_rate'],buffer_frames=meta['buffer'])
            save(folder/'device-start.json',device)
            save(folder/'control.json',dict(port=port,pid=proc.pid,head=build['head'],epoch=epoch.stem))
            yield port
            last_epoch=max(driver.glob('epoch-*.json'),key=lambda p:p.stat().st_mtime_ns)
            last_meta=json.loads(last_epoch.read_text())
            assert last_epoch == epoch, 'Unexpected driver reopen'
            cmd(port,'mix.record_arm',tracks=[track],value=False)
            cmd(port,'ui.audio_device',system=None,output=None,input=None,buffer_size=None)
            time.sleep(.4)
            save(folder/'device-end.json',dict(device='Model Mixer ASIO',sample_rate=last_meta['sample_rate'],buffer_frames=last_meta['buffer']))
        finally:
            if proc.poll() is None: proc.terminate();proc.wait(timeout=15)

def capture_chase(f, pilot):
    import threading
    with desktop(f,hw/'audio/manual-stimulus/chase-135s.wav') as port:
        cmd(port,'setup.mtc',input='UM-ONE',online=True,freewheel='frames',freewheel_frames=8)
        time.sleep(.9)
        status=cmd(port,'setup.mtc')
        if not status['online'] or status['status']=='Input unavailable': raise RuntimeError(status)
        with live_midi(rx_name='UM-ONE') as (_, inbox, names), (f/'wire.csv').open('x',newline='') as wire, (f/'transport.jsonl').open('x',buffering=1) as states:
            rows=csv.writer(wire);rows.writerow(['qpc_ns','hex'])
            save(f/'ready.json',dict(ports=names,mtc=status,qpc_ns=time.perf_counter_ns()))
            if pilot:
                thread=threading.Thread(target=source,args=(f,'Model 12 MIDI',mtc('30',1)))
                thread.start()
            start=time.monotonic();poll=start
            last=0; count=0; segments=[]
            while time.monotonic()-start < (14 if pilot else 1500):
                now=time.monotonic()
                while not inbox.empty():
                    stamp,msg,_=inbox.get_nowait()
                    if msg[0]==0xfe: continue
                    rows.writerow([stamp,bytes(msg).hex()])
                    if msg[0]==0xf1:
                        if not count: first=stamp
                        last=stamp;count+=1
                if count and time.perf_counter_ns()-last>1_000_000_000:
                    segments.append(dict(first=first,last=last,n=count));count=0;wire.flush()
                    save(f/'segments.json',segments)
                    if len([s for s in segments if s['n']>(200 if pilot else 6000)]) >= (1 if pilot else 3): break
                if now>=poll:
                    print(json.dumps([time.perf_counter_ns(),cmd(port,'setup.midi_sync_status'),cmd(port,'transport.status'),time.perf_counter_ns()]),file=states)
                    poll=now+.12
                time.sleep(.01)
            else: raise TimeoutError(f'Incomplete MTC segments {segments}')
            if pilot: thread.join(2)
        cmd(port,'setup.mtc',online=False)
        cmd(port,'transport.stop')

def sd(f):
    with desktop(f,hw/'audio/manual-stimulus/sd-840s.wav') as port:
        cmd(port,'transport.rtz')
        save(f/'ready.json',dict(port=port))
        deadline=time.monotonic()+1500
        while not (f/'recording-confirmed').exists():
            if time.monotonic()>deadline: raise TimeoutError('Awaiting recorder')
            time.sleep(.2)
        save(f/'playing.json',cmd(port,'transport.play'))
        time.sleep(609)
        save(f/'stopped.json',cmd(port,'transport.stop'))
if __name__=='__main__':
    folder=Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN'])
    if sys.argv[1]=='sd': sd(folder)
    else: capture_chase(folder,sys.argv[1]=='pilot')

