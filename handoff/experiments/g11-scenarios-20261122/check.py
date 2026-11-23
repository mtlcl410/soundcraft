from pathlib import Path
import re,json,sys
from publish import cli,fetch,root
f=(root/'REPORT.zh-TW.md').read_text(encoding='utf-8')
ids=re.findall(r'^\| ([A-E])-([0-9]+) \|',f,re.M)
assert len(ids)==len(set(ids))==38 and 'DRIFT_RESULT' not in f and 'LOAD_RESULT' not in f
for target in re.findall(r'\]\(([^)]+)\)',f):
    assert target.startswith('https://') or (root/target).exists(),target
for n in [1662,1663,1669]:
    live=fetch(str(n)); orig=json.loads((root/f'pr-{n}.json').read_text(encoding='utf-8-sig'));url=(root/f'comment-{n}.url').read_text(encoding='utf-8-sig').strip()
    assert live['isDraft'] and live['headRefOid']==orig['headRefOid']
    pattern=r'<!-- g11-scenario-audit-20261122 -->.*?<!-- /g11-scenario-audit-20261122 -->'
    old=orig['body'].splitlines(); restored=re.sub(pattern,'',live['body'],flags=re.S).splitlines()
    it=iter(restored)
    assert all(any(line.rstrip()==actual.rstrip() for actual in it) for line in old if line.strip()),n
    assert url in live['body']; c=json.loads(cli('api','repos/storytold/soundcraft/issues/comments/'+url.rsplit('-',1)[-1]))
    assert re.sub(r'\s+',' ',c['body']).strip()==re.sub(r'\s+',' ',(root/f'public-{n}.md').read_text(encoding='utf-8-sig')).strip()
    print(n,live['headRefOid'][:8],url,'draft, body and comment verified')
print(len(ids),'unique required IDs and all local report links verified')
