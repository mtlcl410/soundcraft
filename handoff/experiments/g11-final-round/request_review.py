"""Ask GitHub for a review of the published MTC revision, without a mention."""
from pathlib import Path
import json,os,subprocess

d=Path(__file__).resolve().parent
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config'}
gh='E:/soundcraft/tools/gh/bin/gh.exe'
base='repos/storytold/soundcraft'
def call(path,method='GET',data=None):
    args=[gh,'api',f'{base}/{path}','-X',method]
    if data is not None: args+=['--input','-']
    return subprocess.run(args,input=None if data is None else json.dumps(data).encode(),env=env,capture_output=True)
pr=json.loads(call('pulls/1663').stdout)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=d/'mtc',text=True).strip()
assert pr['head']['sha']==head and pr['draft']
dest=d/'evidence'/f'1663-{head[:8]}'
done=dest/'review-request.log'
assert not done.exists()
result=call('pulls/1663/requested_reviewers','POST',{'reviewers':['coderabbitai[bot]']})
done.write_bytes(result.stdout+b'\n'+result.stderr)
if result.returncode==0:
    print('Requested reviewers:',[u['login'] for u in json.loads(result.stdout).get('requested_reviewers',[])])
else:
    print(result.stderr.decode(errors='replace'))
raise SystemExit(result.returncode)
