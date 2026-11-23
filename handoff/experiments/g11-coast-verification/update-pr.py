import json, os, subprocess, re, sys
from pathlib import Path
d=Path(__file__).resolve().parent
env=dict(os.environ,GH_CONFIG_DIR='E:/soundcraft/tools/gh-config')
gh='E:/soundcraft/tools/gh/bin/gh.exe'
def cli(*args):return subprocess.check_output([gh,*args],env=env).decode('utf-8').strip()
def view():
    return json.loads(cli('pr','view','1669','-R','storytold/soundcraft','--json','headRefOid,body,isDraft'))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=d/'tree').decode().strip()
v=view(); assert v['headRefOid']==head and v['isDraft']
body=v['body']
old='Should a rolling Coast session relock on F8 alone when the replacement source sends no Start/Continue? The last of 65 attacks was 473.438 ms late. '
assert old in body
new=body.replace(old,'')
opener='## Known limits'
assert new.count(opener)==1 and '## Coast recovery when the external clock returns' not in new
summary=(d/'public-section.md').read_text(encoding='utf-8-sig').replace('COMMIT_SHA',head[:8]).strip()
new=new.replace(opener,summary+'\n\n'+opener,1)
payload=d/'body-update.json'
payload.write_bytes(json.dumps({'body':new},ensure_ascii=True).encode('utf-8'))
assert view()['body']==body
reply=json.loads(cli('api','--method','PATCH','repos/storytold/soundcraft/pulls/1669','--input',str(payload)))
after=view()
assert after['body']==reply['body'] and summary in after['body'] and old not in after['body'] and after['headRefOid']==head and after['isDraft']
print('Verified',head,reply['html_url'],'draft; Open questions preserved except resolved Coast item.')
