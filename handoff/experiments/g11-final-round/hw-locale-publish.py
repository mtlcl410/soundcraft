from pathlib import Path
import os,re,json,subprocess,time,sys
d=Path(__file__).resolve().parent
e=d/'evidence'/'hw-locale'
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config','GIT_TERMINAL_PROMPT':'0'}
gh='E:/soundcraft/tools/gh/bin/gh.exe'
def run(args,cwd=d,data=None):return subprocess.run(args,cwd=cwd,env=env,check=True,input=data,capture_output=True).stdout.decode('utf8')
def api(path,data=None):
    args=[gh,'api','repos/storytold/soundcraft/'+path]
    if data is not None:args+=['-X','PATCH','--input','-']
    return json.loads(run(args,data=None if data is None else json.dumps(data).encode('utf8')))
for n,tree,lower in [(1662,'beat',None),(1663,'mtc','beat'),(1669,'follow','mtc')]:
    if len(sys.argv)>1 and str(n) not in sys.argv[1:]: continue
    w=d/tree
    def git(*args):return run(['git',*args],w).strip()
    assert not git('status','--porcelain') and not git('diff','58061298','--','crates/ui-egui/locales/pt-BR/mod.rs')
    head=git('rev-parse','HEAD')
    results=[r for r in json.loads((e/'results.json').read_text()) if r['pr']==n]
    assert len(results)==2 and all(r['code']==0 and r['head']==head for r in results)
    count=re.search(r'(\d+) passed;',results[-1]['result'][0])[1]
    refdata=json.loads((e/f'{n}-before.json').read_text(encoding='utf8'))
    pr=api(f'pulls/{n}')
    assert pr['draft'] and pr['head']['ref']==refdata['head']['ref'] and pr['head']['repo']['full_name']=='mtlcl410/soundcraft'
    old=refdata['head']['sha']
    assert pr['head']['sha'] in (old,head)
    git('merge-base','--is-ancestor',old,head)
    if lower:
        prerequisite=run(['git','-C',str(d/lower),'rev-parse','HEAD']).strip()
        git('merge-base','--is-ancestor',prerequisite,head)
    if pr['head']['sha']!=head:
        git('-c','credential.helper=','-c','credential.helper=!E:/soundcraft/tools/gh/bin/gh.exe auth git-credential','push','https://github.com/mtlcl410/soundcraft.git','HEAD:refs/heads/'+pr['head']['ref'])
        for _ in range(25):
            if api(f'pulls/{n}')['head']['sha']==head:break
            time.sleep(2)
        assert api(f'pulls/{n}')['head']['sha']==head
    print('pushed',n,head,flush=True)
    runs=[]
    for _ in range(10):
        runs=api('actions/runs?head_sha='+head+'&per_page=30')['workflow_runs']
        if {'CI','ast-grep','SonarCloud','Nix'} <= {r['name'] for r in runs}:break
        time.sleep(2)
    ci=', '.join(x['name']+' `'+(x['conclusion'] or x['status'])+'`' for x in sorted(runs,key=lambda v:v['name'])) if runs else 'no workflow runs listed yet'
    previous=refdata['body']
    old_header=re.search(r'## Verification on the exact head\n\nWindows, [^\n]+\n\n',previous)
    if old_header is None:old_header=re.search(r'## Verification on the exact head\r\n\r\nWindows, [^\n]+\n\r?\n',previous)
    assert old_header,repr(previous[:280])
    note=(f"## Verification\n\nWindows, current head `{head}`. "
          "The Beat Clock labels and diagnostics fall back to English until translations are supplied by craft-i18n. "
          f"The pt-BR catalog matches upstream main at this revision. GitHub Actions: {ci}.\n\n"
          f"| Current-head check | Result |\n| --- | --- |\n| `{results[-1]['command']}` | {count} passed |\n"
          "| `cargo fmt --all -- --check` | Passed |\n\n"
          f"Earlier full-suite and regression results below were measured on `{old[:8]}`.\n\n")
    body=previous[:old_header.start()]+note+previous[old_header.end():]
    assert not re.search(r'(?:^|\s)@[a-zA-Z0-9]', body)
    assert body.split('## Hardware status')[1] == previous.split('## Hardware status')[1]
    now=api(f'pulls/{n}')
    assert now['head']['sha']==head and now['draft']
    assert now['body']==previous or now['body']==body
    (e/f'{n}-after.md').write_text(body,encoding='utf8')
    if now['body']!=body:api(f'pulls/{n}',{'body':body})
    now=api(f'pulls/{n}')
    assert now['head']['sha']==head and now['draft'] and now['body'].replace('\r\n','\n')==body.replace('\r\n','\n')
    (e/f'{n}-final.json').write_text(json.dumps({'head':head,'base':now['base']['ref'],'draft':now['draft'],'branch':now['head']['ref'],'ci':ci,'focused_tests':int(count),'fmt':True},indent=2),encoding='utf8')
    print('verified',n,count,ci,flush=True)

