from common import *
for n in sys.argv[1:]:
 repo=api(base+'pulls/'+n)
 head=repo['head']['sha']
 workflow=api(base+f'actions/runs?head_sha={head}&per_page=40')['workflow_runs']
 checks=', '.join(f"{r['name']} `{r['conclusion'] or r['status']}`" for r in workflow)
 s=re.sub(r'GitHub Actions on this head: [^\n]+?\.(?=\s*\n)',lambda _:f'GitHub Actions on this head: {checks}.',repo['body'],count=1)
 if workflow:s=s.replace('No hosted workflow run is listed for this head yet.',f'GitHub Actions on this head: {checks}.')
 if s!=repo['body']:
  assert head in s and repo['draft']
  assert api(base+'pulls/'+n,'-X','PATCH',payload={'body':s})['body']==s
 (ev/f'{n}-{head[:8]}'/'verified-body.md').write_text(s,'utf8')
 save(f'ci-{n}-{head[:8]}.json',[{k:r[k] for k in ['id','name','head_sha','status','conclusion','html_url']} for r in workflow])
 print(n,head,checks)

