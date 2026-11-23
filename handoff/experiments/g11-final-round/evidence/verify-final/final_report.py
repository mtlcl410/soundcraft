from common import *
def totals(rows):
 passed=failed=ignored=0
 for r in rows:
  if not r['result']: continue
  m=re.search(r'(\d+) passed; (\d+) failed; (\d+) ignored',r['result'][0])
  a,b,c=map(int,m.groups())
  passed+=a;failed+=b;ignored+=c
 return passed,failed,ignored
if __name__=='__main__':
 heads={}
 lines=['## 最後複核 R-1 至 R-6','', '| PR | 最新提交 | 通過 | 失敗 | 預設略過 | 驗證 |','|---|---|---:|---:|---:|---|']
 for n,tree in [('1662','beat'),('1663','mtc'),('1669','follow')]:
  head=git(tree,'rev-parse','HEAD')
  p=api(base+'pulls/'+n)
  assert p['draft'] and p['head']['sha']==head and re.search(r'## Open questions\s+None\.',p['body'])
  folder=ev/f'{n}-{head[:8]}'; rows=json.loads((folder/'results.json').read_text('utf8'))
  url=(folder/'owner-evidence-url.txt').read_text('utf8')
  passed,failed,ignored=totals(rows)
  lines.append(f'| #{n} | `{head}` | {passed} | {failed} | {ignored} | [公開驗證]({url}) · [本機逐項輸出](evidence/{folder.name}/results.json) |')
  heads[n]=head
 for tree,low in [('mtc','1662'),('follow','1663')]:git(tree,'merge-base','--is-ancestor',heads[low],heads['1663' if tree=='mtc' else '1669'])
 lines+=['', (local/'final-notes.md').read_text('utf8').strip(),'']
 s='\n'.join(lines)
 dest=d/'STATUS.zh-TW.md'; old=dest.read_text('utf8')
 start='<!-- BEGIN G11 POST-VERIFY -->';end='<!-- END G11 POST-VERIFY -->'
 if start in old:old=old.split(start)[0].rstrip()
 dest.write_text(old.rstrip()+'\n\n'+start+'\n'+s+'\n'+end+'\n','utf8')

