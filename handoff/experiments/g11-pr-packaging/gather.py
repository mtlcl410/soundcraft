from pathlib import Path
import re,json,hashlib,subprocess as sp,urllib.request,concurrent.futures,html
D=Path(__file__).resolve().parent
read=lambda x:(D/x).read_text(encoding='utf-8-sig')
data={n:json.loads(read(f'pr{n}.json')) for n in [1662,1663,1669]}
root=r'E:/soundcraft/compatibility-audit/g11-clock-stress/publish'
sha=data[1669]['head']['sha']
def src(n, heading):
 s=read('original'+str(n)+'.md')
 return re.search(r'^## '+re.escape(heading)+r'\s*\n(.*?)(?=^## |\Z)',s,re.M|re.S)[1].strip()
def img(match):
 alt,p=match.groups()
 url=f'https://raw.githubusercontent.com/mtlcl410/soundcraft/{sha}/docs/{p}'
 images.append((p,url));return f'![{alt}]({url})'
images=[]
hw=re.sub(r'!\[([^\]]*)\]\((images/[^)]+)\)',img,read('model-12-clock-follow-hardware.md'))
assert len(set(images))==11
def verify(item):
 p,url=item
 data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SoundCraft-PR-documentation'}),timeout=30).read()
 blob=sp.check_output(['git','-C',root,'show',sha+':docs/'+p])
 assert data.startswith(bytes.fromhex('89504e470d0a1a0a')) and data==blob
 return f'{hashlib.sha256(blob).hexdigest()}  docs/{p}'
with concurrent.futures.ThreadPoolExecutor(6) as ex: verified=list(ex.map(verify,images))
(D/'images.sha256').write_text('\n'.join(verified)+'\n',encoding='utf8')
def excerpt(n,title):return re.sub(r'<!--.*?-->','',src(n,title),flags=re.S).strip()
def fold(label,content):return '<details>\n<summary>'+label+'</summary>\n\n'+content.strip()+'\n\n</details>'
intro='''## G-11 verification evidence

The two follow reports below preserve the hardware measurements, the signal paths, and the software-rendered PCM results. Positive timing errors mean late arrivals. The eleven figures are embedded at an immutable revision. Each report identifies its test conditions. The expandable records at the end also cover Beat Clock output and MTC generation/chase. No measurements were repeated for this documentation update.'''
parts=[intro,hw.replace('# External MIDI Beat Clock follow','## External MIDI Beat Clock follow',1),read('external-clock-response-measurements.md').replace('# External MIDI Beat Clock response','## External MIDI Beat Clock response',1)]
for n in [1662,1663]:
 parts.append(fold(f'#{n} — '+('Beat Clock output' if n==1662 else 'MIDI Time Code')+' verification records', '\n\n'.join('### '+h+'\n\n'+excerpt(n,h) for h in ['Hardware status','A-10 verification after output timing loss','Fourth-round changes and verification'])))
text='\n\n'.join(parts)+'\n'
# Historic report links into the repository must remain pinned if they were written as relative links.
assert not re.search(r'(?<!\w)@[A-Za-z0-9_-]+', text)
assert len(text)<65000
(D/'evidence.md').write_text(text,encoding='utf8')
print('characters',len(text),'images',len(images),'nonabsolute links',re.findall(r'\]\((?!https?://|#)([^)]+)\)',text))
