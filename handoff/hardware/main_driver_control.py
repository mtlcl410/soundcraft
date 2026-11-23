"""Plain upstream main, official Model Mixer ASIO, same duplex channels and settings."""
import json,os,socket,subprocess,time
from pathlib import Path
from manual_run import hw,save,cmd
from desktop_sync import rpc
from m1 import np
def run(f):
    e=hw/'audio/build/soundcraft-85623f28.exe'
    driver=f/'driver';driver.mkdir()
    cfg=f/'private-settings';cfg.mkdir()
    with socket.socket() as sk:sk.bind(('127.0.0.1',0));p=sk.getsockname()[1]
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    env=os.environ|dict(SOUNDCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(cfg),SC_ASIO_EVIDENCE=str(driver),SC_ASIO_RETURN_INDEX='8')
    with (f/'application.log').open('xb') as log:
        proc=subprocess.Popen([e,'--control',str(p)],env=env,cwd=f,stdout=log,stderr=log,startupinfo=si)
        try:
            for _ in range(180):
                try:cmd(p,'transport.status');break
                except OSError:time.sleep(.25)
            cmd(p,'session.new',name='ASIO environment control',sample_rate=48000)
            t=cmd(p,'track.new',kind='audio',name='Silent loopback capture')['tracks'][0]
            cmd(p,'mix.mute',tracks=[t],value=True)
            configured=cmd(p,'ui.audio_device',system='ASIO',input='Model Mixer ASIO',output='Model Mixer ASIO',sample_rate=48000,buffer_size=256)
            save(f/'configuration.json',configured)
            cmd(p,'mix.record_arm',tracks=[t],value=True)
            begin=time.perf_counter_ns()
            time.sleep(10)
            end=time.perf_counter_ns()
            save(f/'inspect.json',rpc(p,'ui.inspect',{}))
            records=list(driver.glob('epoch-*.json'))
            cmd(p,'mix.record_arm',tracks=[t],value=False)
            cmd(p,'ui.audio_device',system=None,input=None,output=None,buffer_size=None)
            time.sleep(.5)
            result=dict(head='85623f28f99a9a788123f0f6b48829f95f07962f',requested=dict(sample_rate=48000,buffer=256,input=9,output=1),observed_seconds=(end-begin)/1e9,epochs=len(records),native_interval_ms=None,device=configured.get('device'))
            if len(records)==1:
                meta=json.loads(records[0].read_text());n=meta['buffer'];hz=meta['qpc_frequency']
                block=np.fromfile(records[0].with_suffix('.bin'),dtype=np.dtype([('pre','V16'),('qpc','<u8'),('rest',f'V{16+n*8}')]))
                times=block['qpc'].astype(float)/hz
                gaps=np.diff(times[(times>=begin/1e9)&(times<=end/1e9)])*1000
                if len(gaps):result.update(native_interval_ms=round(float(np.median(gaps)),4),count=len(gaps),min_ms=float(min(gaps)),max_ms=float(max(gaps)))
            save(f/'result.json',result)
        finally:
            if proc.poll() is None:proc.terminate();proc.wait(timeout=12)
if __name__=='__main__':run(Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN']))

