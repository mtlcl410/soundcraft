from pathlib import Path
import json, os, subprocess, sys, time, re
d=Path('E:/soundcraft/compatibility-audit/g11-final-round')
ev=d/'evidence'
local=ev/'verify-final'
gh='E:/soundcraft/tools/gh/bin/gh.exe'
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config','PYTHONUTF8':'1'}
def run(*args,cwd=d,stdin=None):
 return subprocess.check_output(list(args),cwd=cwd,env=env,input=stdin,encoding='utf-8').strip()
def api(path,*args,payload=None):
 argv=[gh,'api',path,*args]
 if payload is not None: argv+=['--input','-']
 return json.loads(run(*argv,stdin=None if payload is None else json.dumps(payload,ensure_ascii=False)))
base='repos/storytold/soundcraft/'
def save(name,v): (local/name).write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')
def git(tree,*args):return run('git','-C',str(d/tree),*args)

