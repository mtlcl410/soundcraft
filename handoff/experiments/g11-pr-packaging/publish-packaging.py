from pathlib import Path
import json,subprocess as sp,re,os,time
d=Path(__file__).resolve().parent;gh=r'E:/soundcraft/tools/gh/bin/gh.exe'
def git(w,*args):return sp.check_output(['git','-C',str(w),*args]).decode('utf8').strip()
def api(route,*args):return json.loads(sp.check_output([gh,'api',route,*args]))
prs=[];base=json.loads((d/'pr1662.json').read_text(encoding='utf-8-sig'))['base']['sha']
for n,count in [(1662,33),(1663,44),(1669,78)]:
 w=d/f'publish{n}';init=json.loads((d/f'pr{n}.json').read_text(encoding='utf-8-sig'))
 target=git(w,'rev-parse','HEAD')
 assert git(w,'status','--porcelain')==''
 git(w,'merge-base','--is-ancestor',init['head']['sha'],target)
 if n!=1662:
  assert git(w,'rev-parse','HEAD^2')==base
 files=git(w,'diff','--name-status',base+'...HEAD').splitlines()
 assert len(files)==count and not any(re.search(r'(?:\.csv|\.log|\.tmp|\.patch|\.png|\.bak|\.etl|\.wav)$|(?:^|/)scripts/',l,re.I) for l in files)
 assert all(l.split('\t')[-1] in (d/f'audit{n}.md').read_text(encoding='utf-8-sig') for l in files)
 git(w,'diff','--check',init['head']['sha'],target)
 actual_rs={l for l in git(w,'diff','--name-only',init['head']['sha'],target).splitlines() if l.endswith('.rs')}
 assert actual_rs<={'crates/playback/src/'+s for s in ['sync_output.rs','sync_output_tests.rs','sync_timing_test.rs','mtc_sync_output_tests.rs','mtc_input.rs','tests.rs']},actual_rs
 s=(d/f'body{n}.md').read_text(encoding='utf-8-sig').strip()
 assert re.findall(r'^## (.*)$',s,re.M)==['What this PR does','Verification on the current head','Hardware status','Known limits','Open questions','Merge order']
 assert len(s)*3<=len(init['body'].replace('\r','')) and not re.search(r'(?<!\w)@[\w-]+',s) and '#issuecomment-7072496268' in s
 info=api(f'repos/storytold/soundcraft/pulls/{n}')
 assert init['head']['sha']==info['head']['sha'] and init['body']==info['body'] and info['draft'] and info['head']['repo']['full_name']=='mtlcl410/soundcraft'
 prs.append((n,w,init,target,s))
 base=target
print('passed static checks',[(n,h[:8],len(b)) for n,w,i,h,b in prs],flush=True)
results=[]
for n,w,i,h,s in prs:
 branch=i['head']['ref'];route=f'repos/storytold/soundcraft/pulls/{n}'
 git(w,'-c','credential.helper=','-c',f'credential.helper=!{gh} auth git-credential','push','https://github.com/mtlcl410/soundcraft.git',f'HEAD:refs/heads/{branch}')
 for k in range(20):
  curr=api(route)
  if curr['head']['sha']==h:break
  time.sleep(2)
 assert curr['head']['sha']==h and curr['body']==i['body']
 path=d/f'publish-body-{n}.json';path.write_text(json.dumps({'body':s},ensure_ascii=False),encoding='utf8')
 patched=api(route,'-X','PATCH','--input',str(path))
 assert patched['head']['sha']==h and patched['body'].replace('\r','')==s and patched['draft']
 size=len(patched['body']);results.append({'pr':n,'head':h,'body_before':len(i['body']),'body_after':size})
 (d/'published.json').write_text(json.dumps(results,indent=2),encoding='utf8')
 print('verified',n,h[:8],size,flush=True)
