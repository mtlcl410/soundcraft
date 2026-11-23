from pathlib import Path
import json, os, socket, subprocess, sys, time, wave, shutil
from m1 import stimulus, read_blocks, measure, rate
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parents[1]/'g11-hardware'))
from desktop_sync import cmd

def apply(port,n):
    answer=cmd(port,'ui.audio_device',system='ASIO',input='Model Mixer ASIO',output='Model Mixer ASIO',sample_rate=rate,buffer_size=n)
    state=answer['device']
    if state['silent'] or state['sample_rate']!=rate or state['name']!='Model Mixer ASIO':raise RuntimeError(answer)
    return answer

def run(folder,exe,n,count):
    shared=folder/'driver';shared.mkdir()
    pcm,_=stimulus()
    wav=folder/'markers.wav'
    with wave.open(str(wav),'wb') as w:
        w.setparams((1,2,rate,0,'NONE',''));w.writeframes(pcm.tobytes())
    with socket.socket() as sk:
        sk.bind(('127.0.0.1',0));port=sk.getsockname()[1]
    settings=folder/'private-settings';settings.mkdir()
    env=os.environ|dict(SOUNDCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(settings),SC_ASIO_EVIDENCE=str(shared),SC_ASIO_RETURN_INDEX='8')
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    with (folder/'application.log').open('wb') as log:
        proc=subprocess.Popen([str(exe),'--control',str(port)],cwd=folder,env=env,startupinfo=si,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(180):
                if proc.poll() is not None:raise RuntimeError('desktop exited')
                try: cmd(port,'transport.status');break
                except OSError:time.sleep(.25)
            cmd(port,'session.new',name='ASIO hardware ruler',sample_rate=rate)
            cmd(port,'file.import_audio',path=str(wav),new_tracks=True,at=0)
            t=cmd(port,'track.new',kind='audio',name='Muted capture')['tracks'][0]
            cmd(port,'mix.mute',tracks=[t],value=True)
            for i in range(count):
                dest=folder/f'take-{i+1:02d}';dest.mkdir()
                before=set(shared.glob('epoch-*.json'))
                setup=apply(port,n)
                cmd(port,'mix.record_arm',tracks=[t],value=True)
                for _ in range(80):
                    epochs=set(shared.glob('epoch-*.json'))-before
                    if epochs:break
                    time.sleep(.1)
                if len(epochs)!=1:raise RuntimeError(f'Expected one new duplex ASIO epoch, saw {epochs}')
                meta_path,=epochs
                cmd(port,'transport.rtz')
                cmd(port,'transport.play')
                time.sleep(2.7)
                cmd(port,'transport.stop')
                cmd(port,'mix.record_arm',tracks=[t],value=False)
                # Release ASIO before requesting another cold open of the same driver.
                cmd(port,'ui.audio_device',system=None,input=None,output=None,buffer_size=None)
                time.sleep(.35)
                for f in (meta_path,meta_path.with_suffix('.bin')):shutil.move(f,dest/f.name)
                meta,_,blocks=read_blocks(dest)
                device=dict(device='Model Mixer ASIO',sample_rate=meta['sample_rate'],buffer_frames=int(blocks['n'][0]))
                if i==0:(folder/'device-start.json').write_text(json.dumps(device))
                (folder/'device-end.json').write_text(json.dumps(device))
                if device['sample_rate']!=rate or device['buffer_frames']!=n:raise ValueError(device)
                summary=measure(dest)
                (dest/'summary.json').write_text(json.dumps(summary,indent=2))
                (dest/'audio-setup.json').write_text(json.dumps(setup,indent=2))
                print(i+1,summary['offsets'],flush=True)
        finally:
            if proc.poll() is None:proc.terminate();proc.wait(timeout=15)
if __name__=='__main__':
    run(Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN']),Path(sys.argv[1]).resolve(),int(sys.argv[2]),int(sys.argv[3]))
