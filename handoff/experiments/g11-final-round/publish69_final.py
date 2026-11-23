from pathlib import Path
import json,os,sys,subprocess,time
d=Path(__file__).resolve().parent
ev=d/'evidence'
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config','PYTHONUTF8':'1'}
gh='E:/soundcraft/tools/gh/bin/gh.exe'
def run(*args):return subprocess.check_output(args,env=env,cwd=d,text=True,encoding='utf8').strip()
def api(path):return json.loads(run(gh,'api','repos/storytold/soundcraft/'+path))
def local(*args):return run(sys.executable,*args)
head=run('git','-C','follow','rev-parse','HEAD')
folder=ev/f'1669-{head[:8]}'
assert api('pulls/1663')['head']['sha']==run('git','-C','mtc','rev-parse','HEAD')
run('git','-C','follow','merge-base','--is-ancestor','final-round-mtc','HEAD')
rows=json.loads((folder/'results.json').read_text('utf8'))
assert len(rows)==7 and rows[-1]['check']=='fmt'
profiles=json.loads((folder/'profiles.json').read_text('utf8'))
assert len(profiles)==13 and all(p['code']==0 and p['head']==head and 'test result: ok.' in p['result'] for p in profiles)
m=json.loads((folder/'review-metrics.json').read_text('utf8'))
assert m['head']==head
evidence=(ev/'comment-1669.md').read_text('utf8')
assert head in evidence and 1000<len(evidence)<65536 and not any(s in evidence for s in ['E:/','E:\\','C:/Users','@coderabbitai'])
print(local('publish.py','1669','follow','push'),flush=True)
pr=api('pulls/1669')
assert pr['draft'] and pr['head']['sha']==head
url_file=folder/'evidence-url.txt'
if url_file.exists():
 url=url_file.read_text().strip()
else:
 url=local('publish.py','1669','follow','evidence')
 url_file.write_text(url)
for _ in range(12):
 runs=api('actions/runs?head_sha='+head+'&per_page=30')['workflow_runs']
 if {'CI','Nix','ast-grep','SonarCloud'} <= {r['name'] for r in runs}:break
 time.sleep(3)
ci='GitHub Actions: '+', '.join(r['name']+' '+(r['conclusion'] or r['status']) for r in runs)+'.' if runs else 'No hosted workflow run is listed yet.'
m['ci']=ci
(folder/'review-metrics.json').write_text(json.dumps(m,indent=2,ensure_ascii=False),'utf8')
local('body69.py',str(folder),url)
body=(ev/'body1669.md').read_text('utf8')
assert len(body.split('## '))==7 and url in body
print(local('publish.py','1669','follow','body'),head,url,ci,flush=True)

