import json,sys
from pathlib import Path
from publish import cli,root
n=1662
url=(root/f'comment-{n}.url').read_text().strip()
api='repos/storytold/soundcraft/issues/comments/'+url.rsplit('-',1)[1]
before=json.loads(cli('api',api))
body=(root/f'public-{n}.md').read_text(encoding='utf-8-sig')
assert before['html_url']==url and 'Unattended G-11 scenario results' in before['body']
dst=root/'comment-1662-update.json'
dst.write_text(json.dumps({'body':body}),encoding='utf-8')
cli('api','--method','PATCH',api,'--input',dst)
assert json.loads(cli('api',api))['body'].strip()==body.strip()
