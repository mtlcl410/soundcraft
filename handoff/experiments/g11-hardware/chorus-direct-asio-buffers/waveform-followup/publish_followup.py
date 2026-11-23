from analysis_audio import *
import os,subprocess,re,hashlib
gh='E:/soundcraft/tools/gh/bin/gh.exe';repo='storytold/soundcraft';env=dict(os.environ,GH_CONFIG_DIR='E:/soundcraft/tools/gh-config')
def run(args):return subprocess.check_output([gh,*args],env=env).decode('utf8')
def view():return json.loads(run(['pr','view','1669','-R',repo,'--json','body,headRefOid,isDraft']))
j=view();sha=j['headRefOid'];assert sha=='f76cef2a4fbd17d04997fc6164e6685c3da3cded' and j['isDraft']
en=(d/'section.en.md').read_text(encoding='utf-8-sig').strip()
zh=(d/'section.zh.md').read_text(encoding='utf-8-sig').strip()
local=src.parent/'ROUND4-ACCEPTANCE.zh-TW.md'
for p in re.findall(r'\]\((chorus-direct-asio-buffers/[^)]+)\)',zh):assert (local.parent/p).is_file(),p
if zh.splitlines()[0] not in local.read_text(encoding='utf-8-sig'):
 with local.open('a',encoding='utf8') as f:f.write('\n'+zh+'\n')
assert zh in local.read_text(encoding='utf-8-sig')
old=j['body'];assert en.splitlines()[0] not in old and old.count('## Open questions')==1
body=old.replace('## Open questions',en+'\n\n## Open questions')
out=d/'pr-updated.md';out.write_bytes(body.encode());run(['pr','edit','1669','-R',repo,'--body-file',str(out)])
a=view();assert a['headRefOid']==sha and a['body'].replace('\r','').strip()==body.replace('\r','').strip() and a['isDraft']
name='midi-clock-asio-waveform-detail.png';blob=json.loads(run(['api','repos/mtlcl410/soundcraft/contents/docs/images/'+name+'?ref='+sha]))['sha'];raw=(d/name).read_bytes();assert blob==hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
print('PR body, head, figure blob and local evidence links verified',sha)

