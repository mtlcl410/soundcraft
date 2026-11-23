"""Publish the exact MTC head and send the single explicitly requested bot command."""
from pathlib import Path
import json,os,subprocess,sys,time
d=Path(__file__).resolve().parent
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config'}
gh='E:/soundcraft/tools/gh/bin/gh.exe'
def call(*args): return subprocess.check_output(args,cwd=d,env=env,text=True,encoding='utf8').strip()
def local(*args): return call(sys.executable,*args)
def api(path):return json.loads(call(gh,'api','repos/storytold/soundcraft/'+path))
sha=call('git','-C','mtc','rev-parse','HEAD')
ev=d/'evidence'; folder=ev/f'1663-{sha[:8]}'
while True:
 try:
  if len(json.loads((folder/'results.json').read_text()))==6 and (ev/'comment-1662-url.txt').exists(): break
 except (FileNotFoundError,json.JSONDecodeError): pass
 time.sleep(4)
local('publish.py','1663','mtc','push')
pr=api('pulls/1663'); assert pr['draft'] and pr['head']['sha']==sha
comment=call(gh,'api','repos/storytold/soundcraft/issues/1663/comments','-X','POST','-f','body=@coderabbitai review','--jq','.html_url')
(folder/'review-command-url.txt').write_text(comment)
(ev/'comment-1663.md').write_text((ev/'mtc-evidence-template.md').read_text(encoding='utf8').replace('VERIFIED_HEAD',sha),encoding='utf8')
local('publish.py','1663','mtc','evidence')
url=(ev/'comment-1663-url.txt').read_text()
local('body63.py',str(folder),url)
runs=api('actions/runs?head_sha='+sha+'&per_page=20')['workflow_runs']
summary=', '.join(f"{r['name']} {r['conclusion'] or r['status']}" for r in runs) or 'no workflow run listed yet'
p=ev/'body1663.md'; p.write_text(p.read_text(encoding='utf8').replace('## Hardware status',f'GitHub Actions: {summary}. [CodeRabbit review requested]({comment}).\n\n## Hardware status'),encoding='utf8')
local('publish.py','1663','mtc','body')
print(sha,comment,url,summary,flush=True)
