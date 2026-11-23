"""Operate a private, silent SoundCraft project through the local control socket."""
from pathlib import Path
import json,os,socket,subprocess,sys,time
root=Path(__file__).resolve().parent

def rpc(port,method,params):
    with socket.create_connection(('127.0.0.1',port),timeout=8) as s:
        s.sendall(json.dumps(dict(id=1,method=method,params=params)).encode()+b'\n')
        r=json.loads(s.makefile('rb').readline())
    if not r.get('ok'): raise ValueError(r)
    return r['result']

def cmd(port,command,**params):
    return rpc(port,'engine.execute',dict(command=command,params=params))

if __name__=='__main__':
    name,action=sys.argv[1:3]
    info=root/(name+'-control.json')
    if action=='start':
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        cfg=root/(name+'-settings')
        cfg.mkdir(exist_ok=True)
        env=dict(os.environ,SOUNDCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(cfg))
        startup=subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow=0
        with (root/(name+'-runtime.log')).open('wb') as log:
            child=subprocess.Popen([root/(name+'-desktop.exe'),'--control',str(port)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env,startupinfo=startup)
        for i in range(180):
            if child.poll() is not None: raise SystemExit('Desktop exited '+str(child.returncode))
            try:
                cmd(port,'transport.status')
                break
            except (OSError,ValueError):
                time.sleep(.25)
        else:
            child.terminate()
            raise SystemExit('Desktop control port timed out')
        cmd(port,'session.new',name='Local MIDI sync acceptance',sample_rate=48000)
        info.write_text(json.dumps(dict(port=port,pid=child.pid)))
        print(cmd(port,'transport.status'))
    elif action=='cmd':
        print(json.dumps(cmd(json.loads(info.read_text())['port'],sys.argv[3],**json.loads(sys.argv[4] if len(sys.argv)>4 else '{}')),ensure_ascii=False))
    elif action=='bench-beat':
        port=json.loads(info.read_text())['port']
        print(cmd(port,'setup.midi_beat_clock',destination=sys.argv[3],offset=0,enabled=True))
        time.sleep(1)
        try:
            print(cmd(port,'transport.play',**{'from':0}))
            time.sleep(3.5)
            print(cmd(port,'transport.stop'))
            time.sleep(.8)
            print(cmd(port,'transport.play',**{'from':48_000}))
            time.sleep(1.3)
        finally:
            print(cmd(port,'transport.stop'))
            time.sleep(.3)
            print(cmd(port,'setup.midi_beat_clock',enabled=False))

