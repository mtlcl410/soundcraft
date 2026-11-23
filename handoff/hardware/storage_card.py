"""Copy only the requested song, compare both SHA-256 digests, then request normal Explorer eject."""
import ctypes,json,os,string,subprocess,sys,time
from pathlib import Path
from sd_crosscheck import copy
hw=Path(__file__).resolve().parent
song=sys.argv[1]
round_no=int(sys.argv[2])
assert len(song.split('_'))==2 and all(x.isdigit() for x in song.split('_')) and round_no in (1,2,3)
cycle=hw/'runs/h3b-model12-01'
def roots():
    mask=ctypes.windll.kernel32.GetLogicalDrives()
    return [Path(f'{letter}:/') for i,letter in enumerate(string.ascii_uppercase) if mask & (1<<i) and ctypes.windll.kernel32.GetDriveTypeW(f'{letter}:\\')==2 and (Path(f'{letter}:/MTR')/song).is_dir()]
until=time.monotonic()+600
while not (volumes:=roots()):
    if time.monotonic()>until:raise TimeoutError('Requested Model 12 card not mounted')
    time.sleep(.5)
if len(volumes)!=1:raise ValueError(volumes)
sd=volumes[0]/'MTR'/song
manifest=dict(root=str(volumes[0]),song=song,files=[{'name':p.name,'bytes':p.stat().st_size} for p in sd.iterdir() if p.is_file()],qpc_ns=time.perf_counter_ns())
(cycle/f'mount-{round_no}.json').write_text(json.dumps(manifest,indent=2))
print(manifest,flush=True)
if round_no==1:copy(song,hw/'runs/m3-sd-01')
# Wait for the separate state sampler to see the transition before normal safe ejection.
time.sleep(3)
env=os.environ|dict(SC_EJECT_LETTER=volumes[0].drive,SC_EJECT_SONG=song)
script="""
$ErrorActionPreference='Stop'
$d=$env:SC_EJECT_LETTER
if ($d -notmatch '^[A-Z]:$') {throw 'Unexpected volume'}
$volume=[IO.DriveInfo]::new($d)
if ($volume.DriveType -ne 'Removable' -or !(Test-Path -LiteralPath (Join-Path $volume.RootDirectory.FullName ('MTR/'+$env:SC_EJECT_SONG)))) {throw 'Card identity changed'}
$shell=New-Object -ComObject Shell.Application
$item=$shell.Namespace(17).ParseName($d)
if (!$item) {throw 'Card missing in Explorer'}
$item.InvokeVerb('Eject')
for ($i=0;$i -lt 80;$i++) { Start-Sleep -Milliseconds 250; if (!$volume.IsReady) {exit 0} }
throw 'Please remain in STORAGE; ejection not confirmed'
"""
subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',script],env=env,check=True)
(cycle/f'ejected-{round_no}.json').write_text(json.dumps(dict(song=song,round=round_no,qpc_ns=time.perf_counter_ns())))
print('Card ejected',flush=True)

