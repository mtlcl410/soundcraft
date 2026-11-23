"""Publish the lower layer after the independent exact-head runner exits."""
from pathlib import Path
import subprocess, json, os, sys, time
d=Path(__file__).resolve().parent
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=d/'beat',text=True).strip()
folder=d/'evidence'/f'1662-{sha[:8]}'
def local(*args):
    subprocess.run([sys.executable,*args],cwd=d,check=True)
while True:
    f=folder/'results.json'
    try:
        rows=json.loads(f.read_text())
    except (FileNotFoundError,json.JSONDecodeError):
        rows=[]
    if len(rows)==5:
        break
    time.sleep(5)
local('publish.py','1662','beat','push')
local('publish.py','1662','beat','evidence')
url=(d/'evidence'/'comment-1662-url.txt').read_text()
local('body62.py',str(folder),url)
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config'}
gh='E:/soundcraft/tools/gh/bin/gh.exe'
runs=json.loads(subprocess.check_output([gh,'api',f'repos/storytold/soundcraft/actions/runs?head_sha={sha}&per_page=20'],env=env))['workflow_runs']
summary=', '.join(f"{r['name']} {r['conclusion'] or r['status']}" for r in runs) or 'no workflow run listed for this revision at the time of verification'
body=d/'evidence'/'body1662.md'
t=body.read_text(encoding='utf8').replace('## Hardware status',f'GitHub Actions: {summary}.\n\n## Hardware status')
body.write_text(t,encoding='utf8')
local('publish.py','1662','beat','body')
print(sha,summary,flush=True)
