"""Publish the verified post-review revision and its findings. No new review request."""
from pathlib import Path
import json, os, re, subprocess, sys, time
d=Path(__file__).resolve().parent
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config','PYTHONUTF8':'1'}
gh='E:/soundcraft/tools/gh/bin/gh.exe'
def run(*args): return subprocess.check_output(args,cwd=d,env=env,text=True,encoding='utf8').strip()
def helper(*args): return run(sys.executable,*args)
def api(path): return json.loads(run(gh,'api','repos/storytold/soundcraft/'+path))
ev=d/'evidence'
head=run('git','-C','mtc','rev-parse','HEAD')
folder=ev/('1663-'+head[:8])
assert not run('git','-C','mtc','status','--porcelain')
log=(folder/'soundcraft-playback.log').read_text('utf8')
exe=re.search(r'Running unittests .*?\(([^\r\n]+\.exe)\)',log).group(1)
helper('profile.py',exe,'matching_rate_with_jitter_never_reports_a_mismatch',str(folder/'ignored-rate.log'),'ignored')
assert '1 passed; 0 failed' in (folder/'ignored-rate.log').read_text('utf8')
review='https://github.com/storytold/soundcraft/pull/1663#pullrequestreview-6010501117'
text=(ev/'cr63-review-response.md').read_text('utf8')
assert 'Pending integrated evidence' not in text and 'LOCAL_ONLY' not in text
text=re.sub(r' *\[(?:Local log|Integrated result)\]\([^)]*\)\.?','',text)
# Publish only reviewer-facing evidence; working notes and local file references stay on disk.
rows=[s for s in text.splitlines() if s.startswith('|')]
assert len(rows)==27
comment=(f'## Verification of the requested changes\n\nThe [review]({review}) covered ten inline findings, fourteen additional findings and one documentation suggestion. The table gives the reproduction and result on `{head}`.\n\n'+'\n'.join(rows)+'\n\n[Earlier red tests and hardware evidence](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074474906).')
assert not re.search(r'(?<!\w)@[a-z\d]',comment,re.I)
(ev/'comment-1663.md').write_text(comment,'utf8')
print(helper('publish.py','1663','mtc','push'),flush=True)
def existing(path,headline):
 comments=json.loads(run(gh,'api','--paginate','--slurp','repos/storytold/soundcraft/'+path))
 return next((c['html_url'] for page in comments for c in page if c['body'].startswith(headline) and head in c['body']),None)
url=existing('issues/1663/comments?per_page=100','## Verification of the requested changes')
if not url:url=helper('publish.py','1663','mtc','evidence')
(folder/'review-resolution-url.txt').write_text(url)
helper('body63.py',str(folder),url)
for _ in range(10):
 runs=api('actions/runs?head_sha='+head+'&per_page=20')['workflow_runs']
 if runs:break
 time.sleep(3)
ci=', '.join(r['name']+' '+(r['conclusion'] or r['status']) for r in runs) or 'no workflow run listed yet'
body=ev/'body1663.md'
s=body.read_text('utf8').replace('## Hardware status',f'GitHub Actions: {ci}. [Formal review]({review}) and [25-item resolution]({url}).\n\n## Hardware status')
body.write_text(s,'utf8')
print(helper('publish.py','1663','mtc','body'),head,url,ci,flush=True)

