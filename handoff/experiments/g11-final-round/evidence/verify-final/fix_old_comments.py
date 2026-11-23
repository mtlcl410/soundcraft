from common import *
n=sys.argv[1]
tree={'1663':'mtc','1669':'follow'}[n]; head=git(tree,'rev-parse','HEAD')
url=(ev/(n+'-'+head[:8])/'owner-evidence-url.txt').read_text('utf8')
cid={'1663':'7074865328','1669':'7074979119'}[n]
path=base+'issues/comments/'+cid
existing=api(path)
s=existing['body']
if n=='1663':
 old='[Reproduction](cr63-red-recovery_status.log)'
 new=f'[Reproduction and regression result]({url})'
else:
 old='on the grouped subset, p99.9 relative to arrival is 34.271 ms.'
 new=f'the previously reported 34.271 ms absolute wire-relative percentile includes an on-grid attack that preceded its F8. At this historical revision, the largest positive software residual during the switch to grouped input was +846 samples (17.625 ms), followed by +642 and +375 samples. See the [new signed measurements]({url}).'
if new not in s:
 assert s.count(old)==1,(old,s[:1000])
 fixed=s.replace(old,new)
 assert api(path,'-X','PATCH',payload={'body':fixed})['body']==fixed
assert new in api(path)['body']
print(existing['html_url'])

