from pathlib import Path
import json,subprocess,os,hashlib,re
d=Path(__file__).resolve().parent;env=dict(os.environ,GH_CONFIG_DIR='E:/soundcraft/tools/gh-config')
gh='E:/soundcraft/tools/gh/bin/gh.exe';repo='storytold/soundcraft'
def run(args):return subprocess.check_output([gh,*args],env=env).decode('utf8')
def view():return json.loads(run(['pr','view','1669','-R',repo,'--json','body,headRefOid,isDraft']))
j=view();sha=j['headRefOid'];assert sha=='9e4f5d8e1aeb99f86c7b440b752adfe1c7bbeefb'
url='https://raw.githubusercontent.com/mtlcl410/soundcraft/'+sha+'/docs/images/midi-clock-asio-buffer-sizes.png'
old=j['body'];section=(d/'pr-section.md').read_text(encoding='utf8').replace('IMAGE_URL',url);assert old.count('## Open questions')==1 and section.splitlines()[0] not in old
body=old.replace('## Open questions',section+'## Open questions')
out=d/'pr-updated.md';out.write_bytes(body.encode('utf8'));run(['pr','edit','1669','-R',repo,'--body-file',str(out)])
after=view()
norm=lambda s:s.replace('\r','').strip()
assert norm(after['body'])==norm(body) and after['headRefOid']==sha and after['isDraft']==j['isDraft']
blob=json.loads(run(['api','repos/mtlcl410/soundcraft/contents/docs/images/midi-clock-asio-buffer-sizes.png?ref='+sha]))['sha']
raw=(d/'midi-clock-asio-buffer-sizes.png').read_bytes();assert blob==hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
report=(d.parent/'ROUND4-ACCEPTANCE.zh-TW.md').read_text(encoding='utf8').split('### Model 12 直接 ASIO 9/10 的緩衝與音訊完整性')[-1]
for p in re.findall(r'\]\((chorus-direct-asio-buffers/[^)]+)\)',report):assert (d.parent/p).is_file(),p
print('PR section, figure blob, head and report links verified:',sha,blob)
