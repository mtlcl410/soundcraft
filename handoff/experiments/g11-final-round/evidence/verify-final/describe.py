from common import *
n,tree=sys.argv[1:3]
head=git(tree,'rev-parse','HEAD')
folder=ev/f'{n}-{head[:8]}'
rows=json.loads((folder/'results.json').read_text('utf-8'))
assert rows[-2]['check']=='clippy' and rows[-2]['code']==rows[-1]['code']==0 and rows[-1]['check']=='fmt'
p=api(base+'pulls/'+n)
assert p['draft'] and p['head']['sha']==head
original=p['body']
(local/f'body-{n}-before.md').write_text(original,'utf-8')
def table():
 out=['| Command | Result |','| --- | --- |']
 for row in rows:
  assert row['head']==head
  if row['result']:
   m=re.search(r'(\d+) passed; (\d+) failed; (\d+) ignored',row['result'][0]); a,b,c=map(int,m.groups())
   result=f'{a} passed'+(f', {b} failed (#1536)' if b else '')+(f', {c} ignored' if c else '')
  else: result='Passed'
  out+=['| `'+row['command']+'` | '+result+' |']
 return '\n'.join(out)
urlfile=folder/'owner-evidence-url.txt'
if not urlfile.exists():
 draft=(local/f'{n}-comment.md').read_text('utf-8').replace('{head}',head)
 assert 0<len(draft)<65000 and head in draft
 data=api(base+f'issues/{n}/comments','-X','POST',payload={'body':draft})
 urlfile.write_text(data['html_url'],'utf-8')
url=urlfile.read_text('utf8')
runs=api(base+f'actions/runs?head_sha={head}&per_page=40')['workflow_runs']
save(f'ci-{n}-{head[:8]}.json',[{k:r[k] for k in ['id','name','head_sha','status','conclusion','html_url']} for r in runs])
names=', '.join(f"{r['name']} `{r['conclusion'] or r['status']}`" for r in runs)
checks=f'GitHub Actions on this head: {names}.' if runs else 'No hosted workflow run is listed for this head yet.'
sections=re.split(r'(?m)^## ',original); assert len(sections)==7
def bodypart(i):return sections[i].split('\n',1)[1].strip()
before,hw,limits,order=map(bodypart,[1,3,4,6])
if n=='1662':
 before+=' Queued MIDI belongs to its originating transport pass. Reconnect retains the selected audio host and port identity.'
 detail='Before the fixes, a superseded locate could still emit its queued SPP, a rejected Stop vanished from the next pass, and a long worker stall exhausted the repayment window without resynchronizing.'
elif n=='1663':
 detail='A stopped monitored locate at sample 42,000 formerly published 41,576. The regression now observes 42,000. The audio recovery and output-scheduler fixes also run independently in #1662. The ten inline review threads are resolved. [Formal review](https://github.com/storytold/soundcraft/pull/1663#pullrequestreview-6010501117) · [25 findings and their verification](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074865328).'
 detail+='\n\nCodeRabbit reviewed the earlier revision. Automatic draft reviews are skipped. [Draft review status](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7027417714)'
 assert '1 passed; 0 failed' in (folder/'ignored-rate.log').read_text('utf8')
 detail+='\n\nAdditional pass: `cargo test --locked -p soundcraft-playback --lib matching_rate_with_jitter_never_reports_a_mismatch -- --ignored`. The test covers four wire rates.'
else:
 data=json.loads((local/'1669-details.json').read_text('utf8'))
 before+=' EXT has no default keyboard shortcut. Ctrl/Cmd+J remains assigned to MTC Online. Setup › MIDI › Sync configures the source. Steady fast Clock loss times out at 150 ms, extending up to 1.5 s during slowdown. With Active Sensing the timeout is 300 ms without MIDI activity. MTC chase uses the session External Timecode Offset alone.'
 detail=data['detail']
 limits=data['limits']
 doc=bodypart(2)
 ignored=doc[doc.index('Reproduce them in PowerShell:'):doc.index('~~~',doc.index('~~~powershell')+3)+3]
 detail+='\n\n'+ignored
s='## What this PR does\n\n'+before+'\n\n## Verification on the exact head\n\nWindows, `'+head+'`. '+checks+'\n\n'+table()+'\n\n'+detail+'\n\n[Verification and red/green evidence]('+url+').\n\n## Hardware status\n\n'+hw+'\n\n## Known limits\n\n'+limits+'\n\n## Open questions\n\nNone.\n\n## Merge order\n\n'+order+'\n'
assert s.count('## ')==6 and not re.search(r'(?<!\w)@[a-z]',s,re.I)
assert api(base+'pulls/'+n)['body']==original
q=api(base+'pulls/'+n,'-X','PATCH',payload={'body':s})
check=api(base+'pulls/'+n)
assert s==check['body'] and check['head']['sha']==head and check['draft']
(folder/'verified-body.md').write_text(s,encoding='utf8')
print(head, url,checks)

