"""Windows preflight and guarded measurement runner, outside the SoundCraft source tree."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
import winreg

import psutil
import win32ts

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def endpoint():
    ole = C.windll.ole32
    init = ole.CoInitializeEx(None, 2)
    def guid(value):
        return (C.c_ubyte * 16).from_buffer_copy(uuid.UUID(value).bytes_le)
    def method(obj, index, result, *args):
        table = C.cast(obj, C.POINTER(C.POINTER(C.c_void_p))).contents
        return C.WINFUNCTYPE(result, C.c_void_p, *args)(table[index])
    obj, dev, name = C.c_void_p(), C.c_void_p(), C.c_void_p()
    try:
        hr = ole.CoCreateInstance(C.byref(guid('BCDE0395-E52F-467C-8E3D-C4579291692E')), None, 1,
                                  C.byref(guid('A95664D2-9614-4F35-A746-DE8DB63617E6')), C.byref(obj))
        if hr or not obj: raise RuntimeError(f'MMDeviceEnumerator {hr}')
        hr = method(obj,4,C.c_long,C.c_int,C.c_int,C.POINTER(C.c_void_p))(obj,0,1,C.byref(dev))
        if hr or not dev: raise RuntimeError(f'GetDefaultAudioEndpoint {hr}')
        hr = method(dev,5,C.c_long,C.POINTER(C.c_void_p))(dev,C.byref(name))
        if hr or not name: raise RuntimeError(f'IMMDevice.GetId {hr}')
        return C.wstring_at(name)
    finally:
        if name: ole.CoTaskMemFree(name)
        for handle in (dev,obj):
            if handle: method(handle,2,C.c_uint32)(handle)
        if init in (0,1): ole.CoUninitialize()

def remote_state():
    return any(row['State']==0 and win32ts.WTSQuerySessionInformation(None,row['SessionId'],win32ts.WTSClientProtocolType)!=0
               for row in win32ts.WTSEnumerateSessions(None))
def capture():
    ps='Get-WinEvent -FilterHashtable @{ProviderName="chromoting";Id=1,2} -MaxEvents 1 -ErrorAction Stop | Select-Object Id,RecordId | ConvertTo-Json -Compress'
    crd=json.loads(subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',ps]))
    power=subprocess.check_output(['powercfg','/getactivescheme'])
    plan=re.search(rb'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',power)
    if not plan: raise RuntimeError('Cannot identify power plan')
    return dict(at=utc(),playback_endpoint=endpoint(),power_plan=plan[0].decode(),rdp_active=remote_state(),asio_panel=driver_preferences(),
                crd_last_event=crd,compilers=compilers())
def driver_preferences():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\TASCAM\ModelMixer\ASIODRIVER') as key:
        return {k:winreg.QueryValueEx(key,k)[0] for k in ('blockFrames','sampleRate')}
def compilers():
    names={'cargo.exe','rustc.exe','cl.exe','link.exe','lld-link.exe','cmake.exe','ninja.exe','msbuild.exe'}
    return sorted({p.info['name'] for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() in names})
def write(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False),'utf8')
def run(args):
    if not args.command or not args.out or not args.panel:raise SystemExit('Expected --out, --panel, and -- command')
    folder=args.out.resolve(); folder.mkdir(parents=True,exist_ok=False)
    panel=json.loads(args.panel.read_text('utf-8-sig'))
    start=capture(); write(folder/'environment-start.json',{'panel_reported':panel,**start})
    reasons=[]
    if start['rdp_active'] or start['crd_last_event']['Id']!=2: reasons.append('Remote session active or not confirmed disconnected')
    if start['compilers']: reasons.append('Build process present')
    if not(str(panel.get('firmware','')).startswith('1.50') and panel.get('output_delay')=='DISABLE'
           and panel.get('usb_audio')=='MULTI INPUT' and panel.get('local_confirmed') is True):
        reasons.append('Missing local panel confirmation')
    sample=psutil.cpu_percent(1)
    if sample>50:reasons.append(f'Busy host before run ({sample}%)')
    cmd=args.command[1:] if args.command[0]=='--' else args.command
    rc=None
    if not reasons:
        proc=subprocess.Popen(cmd,env=os.environ|{'SOUNDCRAFT_ACCEPTANCE_RUN':str(folder)})
        with (folder/'environment-during.jsonl').open('w',encoding='utf8') as f:
            while proc.poll() is None:
                cpu=psutil.cpu_percent(1); active=compilers(); remote=remote_state()
                default=endpoint()
                if active or remote or default!=start['playback_endpoint']: reasons.append('Competing build, remote session or endpoint change during run')
                if cpu>75: reasons.append(f'Busy system during run ({cpu}%)')
                f.write(json.dumps([utc(),cpu,active,remote,default])+'\n')
        rc=proc.returncode
        if rc:reasons.append(f'Measurement process exited {rc}')
    end=capture(); panel_end=json.loads(args.panel.read_text('utf-8-sig'))
    write(folder/'environment-end.json',{'panel_reported':panel_end,**end})
    if panel!=panel_end or any(start[k]!=end[k] for k in ['playback_endpoint','power_plan','rdp_active','crd_last_event','compilers','asio_panel']):
        reasons.append('Environment changed')
    if rc is not None and args.audio:
        for filename in ('device-start.json','device-end.json'):
            if not (folder/filename).exists(): reasons.append('Missing actual driver settings: '+filename)
        if not reasons:
            a,b=[json.loads((folder/x).read_text('utf-8-sig')) for x in ('device-start.json','device-end.json')]
            for key in ('device','sample_rate','buffer_frames'):
                if not a.get(key) or a[key]!=b.get(key):reasons.append('Unverified or changed '+key)
    write(folder/'environment-result.json',dict(environment_valid=not reasons,reasons=list(dict.fromkeys(reasons)),command_exit=rc))
    return int(bool(reasons))
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['snapshot','run'])
    parser.add_argument('--out',type=Path);parser.add_argument('--panel',type=Path);parser.add_argument('--audio',action='store_true')
    argv=sys.argv[1:]; split=argv.index('--') if '--' in argv else len(argv)
    args=parser.parse_args(argv[:split]);args.command=argv[split+1:]
    if args.action=='snapshot':print(json.dumps(capture(),indent=2))
    else:sys.exit(run(args))

