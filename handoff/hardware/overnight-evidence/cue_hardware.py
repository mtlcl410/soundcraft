"""Quiet 48k/256 Model 12 + UM-ONE checks using the previously accepted wiring."""
from pathlib import Path
import os,json,csv,subprocess,sys,statistics
a=Path(__file__).resolve().parent;d=a.parent
def run(label,manifest,seconds):
    folder=a/label
    env=os.environ|{'SC_ACCEPTANCE_BUILD':str(d/'audio/build'/manifest),'PYTHONPATH':os.pathsep.join(map(str,[d/'audio',d/'midi',d]))}
    with (a/(label+'.log')).open('xb') as f:
        rc=subprocess.run([sys.executable,'-X','utf8',str(d/'environment.py'),'run','--panel',str(d/'panel.json'),'--out',str(folder),'--audio','--',
                           sys.executable,'-X','utf8',str(a/'pilot3.py'),str(seconds)],stdout=f,stderr=subprocess.STDOUT,cwd=d,env=env).returncode
    if not (folder/'result.json').exists():raise RuntimeError((label,rc))
    import wire_boundaries
    detail=wire_boundaries.data(folder)
    with (folder/'egress.csv').open() as f:
        rows=list(csv.DictReader(f))
    qf=[int(r['at_ns']) for r in rows if r['hex'].startswith('f1')]
    edge=[(y-x)/1e6 for x,y in zip(qf[:8],qf[1:9])]
    cl=[int(r['at_ns']) for r in rows if r['hex']=='f8']
    detail.update(first_8_qf_intervals_ms=edge,first_8_clock_intervals_ms=[(y-x)/1e6 for x,y in zip(cl[:8],cl[1:9])])
    (folder/'edge-analysis.json').write_text(json.dumps(detail,indent=2))
    status=json.loads((folder/'result.json').read_text());envr=json.loads((folder/'environment-result.json').read_text())
    return dict(label=label,hardware_seconds=seconds,environment_valid=envr['environment_valid'],output_clock=status['received_clock'],expected_clock=status['expected_clock'],
        qf=status['received_qf'],expected_qf=status['expected_qf'],transport=[i['hex'] for i in status['controls']],detail=detail)
if __name__=='__main__':
    # Pass unique labels, not reusable directories; leave every original artifact intact.
    rev=sys.argv[1];prefix=sys.argv[2]
    results=[]
    for i in range(3):
        results.append(run(f'{prefix}-{i+1}',f'{rev}-build.json',24))
        (a/(prefix+'-summary.json')).write_text(json.dumps(results,indent=2))
        print(results[-1]['label'],results[-1]['transport'],results[-1]['output_clock'],results[-1]['qf'],flush=True)
