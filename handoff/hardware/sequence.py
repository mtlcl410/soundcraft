from pathlib import Path
import json, sys, subprocess, time
root=Path(__file__).resolve().parent
output=root/'runs'
def guarded(name,command, audio=False):
    dest=output/name
    args=[sys.executable,str(root/'environment.py'),'run','--panel',str(root/'panel.json'),'--out',str(dest)]
    if audio:args+=['--audio']
    child=subprocess.run([*args,'--',*map(str,command)],check=False)
    return child.returncode==0
if __name__=='__main__':
    # Hold the interfaces idle until the three independent audio runs have closed.
    deadline=time.monotonic()+600
    while not (output/'m1-independent-512-a/environment-result.json').exists():
        if time.monotonic()>deadline:raise TimeoutError('uncompleted independent measurement')
        time.sleep(1)
    if not guarded('m2-identify-a',[sys.executable,root/'midi/routes.py']):raise SystemExit('MIDI port detection invalid')
    routes=json.loads((output/'m2-identify-a/routes.json').read_text())
    for side in ('forward','reverse'):
        options=[r for r in routes if len(r['received'])==4 and all(m==[248] for m,d in r['received']) and ((r['tx']=='UM-ONE')==(side=='forward'))]
        if len(options)!=1:
            print(f'{side}: no unique verified physical route: {options}',flush=True)
            continue
        r=options[0]
        name=f'm2-{side}-a'
        good=guarded(name,[sys.executable,root/'midi/midi_path.py','run','--tx',r['tx'],'--rx',r['rx'],'--out',output/name/'data'])
        print(side,r['tx'],r['rx'],good,flush=True)
    build=root/'audio/build_tools.py'
    with (root/'audio/soundcraft-beat-build.log').open('wb') as log:
        code=subprocess.run([sys.executable,str(build),'soundcraft','--tree',str(root.parent/'g11-final-round/beat')],stdout=log,stderr=subprocess.STDOUT).returncode
    print('SoundCraft build',code,flush=True)
