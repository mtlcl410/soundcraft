import json, subprocess, os, re, sys
from pathlib import Path
root=Path(__file__).resolve().parent
gh='E:/soundcraft/tools/gh/bin/gh.exe'
env=dict(os.environ,GH_CONFIG_DIR='E:/soundcraft/tools/gh-config',GH_PAGER='cat')
repo='storytold/soundcraft'
def cli(*args):
    p=subprocess.run([gh,*map(str,args)],capture_output=True,encoding='utf-8',env=env)
    if p.returncode:
        raise RuntimeError(p.stderr)
    return p.stdout.strip()
def fetch(pr):
    return json.loads(cli('pr','view',pr,'-R',repo,'--json','body,headRefOid,isDraft'))
def publish(pr):
    n=str(pr); live=fetch(n); head=json.loads((root/f'pr-{n}.json').read_text(encoding='utf-8-sig'))['headRefOid']
    assert live['headRefOid']==head
    url_path=root/f'comment-{pr}.url'
    if not url_path.exists():
        url=cli('pr','comment',n,'-R',repo,'--body-file',root/f'public-{n}.md'); assert url.startswith('https://github.com/')
        url_path.write_text(url,encoding='utf-8')
    url=url_path.read_text().strip()
    live=fetch(n); assert live['headRefOid']==head
    body=live['body']; outline=(root/f'open-{n}.md').read_text(encoding='utf-8-sig').strip()
    marker='<!-- g11-scenario-audit-20261122 -->'
    end='<!-- /g11-scenario-audit-20261122 -->'
    appendix=f'{marker}\n### Unattended performance and studio scenarios\n\n{outline}\n\n[Measurements and local regression names]({url})\n{end}'
    if marker in body:
        updated=re.sub(re.escape(marker)+r'.*?'+re.escape(end),lambda _:appendix,body,flags=re.S)
    else:
        q=re.search(r'(?im)^## Open questions[^\r\n]*',body)
        if q: updated=body[:q.end()]+'\n\n'+appendix+'\n'+body[q.end():]
        else:
            bot=re.search(r'(?im)^<!--.*(?:auto-generated|coderabbit).*?-->|^## Summary by CodeRabbit',body)
            pos=bot.start() if bot else len(body)
            updated=body[:pos].rstrip()+'\n\n## Open questions\n\n'+appendix+'\n\n'+body[pos:]
    dst=root/f'published-body-{n}.md'; dst.write_text(updated,encoding='utf-8')
    if updated!=body:
        assert fetch(n)['body']==body, 'concurrent PR description change'
        cli('pr','edit',n,'-R',repo,'--body-file',dst)
    again=fetch(n); assert again['isDraft']==live['isDraft'] and again['headRefOid']==head and url in again['body'] and end in again['body']
    print(n,url,head,flush=True)
for n in sys.argv[1:]: publish(n)
