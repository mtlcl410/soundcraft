"""Private detector-input injection; no STORAGE, slow native callback, or manual reconnect."""
import json,os,socket,subprocess,sys,time
from pathlib import Path
from storage_idle_acceptance import cmd,read_window,save,tone
from score_idle_tone import score

def run(folder,manifest):
    driver=folder/'driver';driver.mkdir()
    settings=folder/'settings';settings.mkdir()
    epochfile=folder/'injection';epochfile.write_text('0')
    binary=json.loads(manifest.read_text());save(folder/'build.json',binary)
    env=os.environ|dict(SOUNDCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(settings),RUST_LOG='info',SC_ASIO_EVIDENCE=str(driver),SC_ASIO_RETURN_INDEX='8',SC_DIAGNOSTIC_EPOCH=str(epochfile))
    with socket.socket() as sk:
        sk.bind(('127.0.0.1',0));port=sk.getsockname()[1]
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    events=[]; windows={}
    def state(label):
        x=dict(label=label,time_ns=time.perf_counter_ns(),epoch_count=len(list(driver.glob('*.json'))),transport=cmd(port,'transport.status'));events.append(x);save(folder/'events.json',events)
        return x
    def window(name):
        a=time.perf_counter_ns();time.sleep(8);windows[name]=[a,time.perf_counter_ns()];save(folder/'windows.json',windows)
    with (folder/'app.log').open('xb') as log:
        p=subprocess.Popen([binary['exe'],'--control',str(port)],cwd=folder,env=env,startupinfo=startup,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(180):
                try:cmd(port,'transport.status');break
                except OSError:time.sleep(.25)
            tone(folder/'a4.wav')
            cmd(port,'session.new',name='Gated ASIO rebuild',sample_rate=48000)
            cmd(port,'file.import_audio',path=str(folder/'a4.wav'),new_tracks=True,at=0)
            t=cmd(port,'track.new',kind='audio',name='Return')['tracks'][0]
            cmd(port,'track.input',track=t,input='In 9')
            cmd(port,'mix.mute',tracks=[t],value=True)
            conf=cmd(port,'ui.audio_device',system='ASIO',input='Model Mixer ASIO',output='Model Mixer ASIO',sample_rate=48000,buffer_size=256)
            save(folder/'config.json',conf)
            assert conf['device']['name']=='Model Mixer ASIO' and not conf['device']['silent'],conf
            cmd(port,'mix.record_arm',tracks=[t],value=True)
            cmd(port,'session.save_as',path=str(folder/'project'/'recording.scraft'))
            time.sleep(1)
            window('baseline')
            for i,mode in enumerate(['stopped','playing','recording'],1):
                cmd(port,'transport.rtz')
                if mode=='playing': cmd(port,'transport.play',**{'from':0})
                if mode=='recording': cmd(port,'transport.record')
                time.sleep(.5)
                before=state(mode+'-before')
                assert before['transport']['playing']==(mode!='stopped') and before['transport']['recording']==(mode=='recording'),before
                epochfile.write_text(str(i))
                if mode!='stopped':
                    time.sleep(6)
                    held=state(mode+'-injected')
                    assert held['epoch_count']==before['epoch_count'] and held['transport']['playing'] and held['transport']['recording']==(mode=='recording'),held
                    cmd(port,'transport.stop')
                for _ in range(100):
                    if len(list(driver.glob('*.json')))>before['epoch_count']:break
                    time.sleep(.2)
                time.sleep(1)
                after=state(mode+'-recovered')
                assert after['epoch_count']==before['epoch_count']+1 and not after['transport']['playing'] and not after['transport']['recording'],after
                cmd(port,'transport.play',**{'from':0});window('play-'+mode)
                cmd(port,'transport.stop');time.sleep(.5)
            cmd(port,'session.save')
            cmd(port,'mix.record_arm',tracks=[t],value=False)
            cmd(port,'ui.audio_device',system=None,input=None,output=None,buffer_size=None)
            time.sleep(1)
        finally:
            if p.poll() is None:p.terminate();p.wait(15)
            result={k:read_window(folder,*bounds) for k,bounds in windows.items()}
            save(folder/'histograms.json',result)
            score(folder)

if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
