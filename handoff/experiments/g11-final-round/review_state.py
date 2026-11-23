"""Read the PR conversation and distinguish an increment review from the draft notice."""
from pathlib import Path
import subprocess,json,os,re,sys
d=Path(__file__).resolve().parent
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config'}
gh='E:/soundcraft/tools/gh/bin/gh.exe'
def pages(path):
 raw=subprocess.check_output([gh,'api','--paginate','--slurp','repos/storytold/soundcraft/'+path],env=env)
 return [v for page in json.loads(raw) for v in page]
def pr(n):return json.loads(subprocess.check_output([gh,'api','repos/storytold/soundcraft/pulls/'+str(n)],env=env))
n=1663
head=pr(n)['head']['sha']
p=d/'evidence'/f'1663-{head[:8]}'
f=p/'review-command-url.txt'
if not f.exists():sys.exit('New increment has not requested a review yet')
id=int(f.read_text().strip().split('-')[-1])
comments=pages(f'issues/{n}/comments?per_page=100')
cmd=next(v for v in comments if v['id']==id)
reviews=[v for v in pages(f'pulls/{n}/reviews?per_page=100') if v['user']['login']=='coderabbitai[bot]' and v['commit_id']==head]
responses=[v for v in comments if v['user']['login']=='coderabbitai[bot]' and v['updated_at']>=cmd['created_at']]
inline=[v for v in pages(f'pulls/{n}/comments?per_page=100') if v['user']['login']=='coderabbitai[bot]' and v['created_at']>=cmd['created_at']]
record={'head':head,'command':cmd['html_url'],'reviews':reviews,'conversation':responses,'inline':inline}
(p/'coderabbit-increment.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf8')
for group in [reviews,responses,inline]:
 for v in group:
  print(v['html_url'], v.get('state',''),v.get('path',''),v.get('body','')[:1300].encode('ascii','backslashreplace').decode())
