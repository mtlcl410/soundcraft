"""Operator-controlled three-cycle run. The only audio-device commands are initial setup and final cleanup."""
import json, os, socket, subprocess, sys, time
from pathlib import Path
from manual_run import cmd, hw, save
from storage_i24_control import np
from storage_cycle import tone

def read_window(run, a, b):
    all_ms, segments = [], []
    for ep in sorted((run/'driver').glob('epoch-*.json')):
        m = json.loads(ep.read_text())
        hz, n = m['qpc_frequency'], m['buffer']
        dt = np.dtype([('pos','<u8'),('sys','<u8'),('q','<u8'),('s','<u8'),('flags','<i4'),('n','<u4'),('pcm','<f4',(n,2))])
        count = ep.with_suffix('.bin').stat().st_size // dt.itemsize
        if not count: continue
        x = np.memmap(ep.with_suffix('.bin'),mode='r',dtype=dt,shape=(count,))
        lo,hi = np.searchsorted(x['q'],np.array([a,b],dtype=float)*hz/1e9)
        w = x[lo:hi]
        if len(w)<2: continue
        gaps = np.diff(w['q'].astype('int64'))*1000/hz
        all_ms.extend(gaps.tolist())
        segments.append(dict(epoch=ep.stem, callbacks=len(w), rate=m['sample_rate'], buffer=n,
                             sample_jumps=int(np.count_nonzero(np.diff(w['pos'].astype('int64'))!=n)),
                             seq_skips=int(np.count_nonzero(np.diff(w['s'])!=1)),
                             peak=np.max(np.abs(w['pcm']),axis=(0,1)).tolist()))
    ms = np.array(all_ms)
    return dict(bounds=[a,b],segments=segments,intervals=len(ms), bins=np.histogram(ms,[0,2,4,7,10,50,200,240,260,np.inf])[0].tolist(),
                mean=float(ms.mean()) if len(ms) else None, median=float(np.median(ms)) if len(ms) else None)

def run(run, manifest):
    startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    driver=run/'driver'; driver.mkdir()
    settings=run/'settings'; settings.mkdir()
    tone(run/'a4.wav')
    binary=json.loads(manifest.read_text()); save(run/'build.json',binary)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    env=os.environ|dict(SOUNDCRAFT_NO_PREFS='1', SOUNDCRAFT_CONFIG_DIR=str(settings), SC_ASIO_EVIDENCE=str(driver), SC_ASIO_RETURN_INDEX='8', RUST_LOG='info')
    with (run/'app.log').open('xb') as log:
        p=subprocess.Popen([binary['exe'],'--control',str(port)],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup)
        windows={}
        def window(name):
            a=time.perf_counter_ns(); time.sleep(8); b=time.perf_counter_ns()
            windows[name]=[a,b]; save(run/'windows.json',windows)
            time.sleep(1.0)
            return read_window(run,a,b)
        try:
            for _ in range(240):
                if p.poll() is not None: raise RuntimeError('desktop exited early')
                try: cmd(port,'transport.status'); break
                except OSError: time.sleep(.25)
            else: raise RuntimeError('control unavailable')
            save(run/'process.json',dict(port=port,pid=p.pid))
            cmd(port,'session.new',name='idle ASIO recovery',sample_rate=48000)
            cmd(port,'file.import_audio',path=str(run/'a4.wav'),new_tracks=True,at=0)
            track=cmd(port,'track.new',kind='audio',name='Muted duplex input')['tracks'][0]
            cmd(port,'mix.mute',tracks=[track],value=True)
            conf=cmd(port,'ui.audio_device',system='ASIO',input='Model Mixer ASIO',output='Model Mixer ASIO',sample_rate=48000,buffer_size=256)
            save(run/'config.json',conf)
            if conf['device']['silent'] or conf['device']['name']!='Model Mixer ASIO': raise RuntimeError(conf)
            cmd(port,'mix.record_arm',tracks=[track],value=True)
            time.sleep(2)
            h=window('baseline');save(run/'baseline.json',h)
            if h['intervals']<1400 or abs(h['mean']-1000*256/48000)>.27 or not all(s['rate']==48000 and s['buffer']==256 for s in h['segments']): raise RuntimeError(h)
            cmd(port,'transport.play',**{'from':0})
            window('play-baseline')
            cmd(port,'transport.stop')
            for i in range(1,4):
                # Two cycles deliberately hold playback open to capture the old stream.
                # In cycle three the user is already stopped when STORAGE starts.
                if i!=3: cmd(port,'transport.play',**{'from':576000})
                time.sleep(.6)
                save(run/f'ready-{i}.json',dict(time=time.perf_counter_ns(),epoch_count=len(list(driver.glob('*.json'))),transport=cmd(port,'transport.status')))
                with (run/f'eject-{i}.log').open('wb') as el:
                    subprocess.Popen(['pwsh','-NoProfile','-File',str(hw/'eject_storage_control.ps1'),'-RunFolder',str(run),'-Cycle',str(i)],cwd=run,stdout=el,stderr=el,startupinfo=startup)
                limit=time.monotonic()+1800
                while not (run/f'restored-{i}').exists():
                    if time.monotonic()>limit: raise TimeoutError('operator still pending')
                    time.sleep(.25)
                if i!=3:
                    window(f'slow-{i}')
                    save(run/f'pre-stop-{i}.json',dict(epoch_count=len(list(driver.glob('*.json'))),transport=cmd(port,'transport.status')))
                    cmd(port,'transport.stop')
                # Remain stopped until a stable, continuous new window has been captured.
                for j in range(6):
                    time.sleep(1.2)
                    h=window(f'idle-{i}-{j}')
                    if h['intervals']>=1400 and 5.07<h['mean']<5.61 and h['bins'][7]==0:
                        break
                else: raise RuntimeError(('Recovery timed out',i,h))
                cmd(port,'transport.play',**{'from':0})
                h=window(f'play-{i}')
                cmd(port,'transport.stop')
                save(run/f'complete-{i}.json',h)
            cmd(port,'mix.record_arm',tracks=[track],value=False)
            cmd(port,'ui.audio_device',system=None,input=None,output=None,buffer_size=None)
            time.sleep(1)
        finally:
            if p.poll() is None: p.terminate();p.wait(15)
            save(run/'histograms.json',{k:read_window(run,*v) for k,v in windows.items()})

if __name__=='__main__':
    run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
