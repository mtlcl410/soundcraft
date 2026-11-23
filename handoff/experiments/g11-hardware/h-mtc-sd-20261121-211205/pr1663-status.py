import sys,subprocess,json
from pathlib import Path
sys.path.insert(0,r'E:/soundcraft/tmp/1669-coderabbit-final')
from check import gh,env,api
ref='repos/storytold/soundcraft/pulls/1663'
p=api(ref);old=p['body']
msg=Path(sys.argv[1]).read_text(encoding='utf-8-sig').strip()
start='<!-- H-MTC-SD-results -->'
end='<!-- end-H-MTC-SD-results -->'
if start in old:
 before,remain=old.split(start,1)
 _,after=remain.split(end,1)
 new=before+start+'\n'+msg+'\n'+end+after
else:
 key='## Known limits and deferred work'
 assert old.count(key)==1 and 'H-MTC-SD' in old
 new=old.replace(key,start+'\n'+msg+'\n'+end+'\n\n'+key)
assert api(ref)['body']==old
subprocess.run([gh,'api','-X','PATCH',ref,'--input','-'],env=env,input=json.dumps({'body':new}).encode(),stdout=subprocess.DEVNULL,check=True)
v=api(ref)
assert v['body']==new and v['head']['sha']==p['head']['sha'] and v['draft']==p['draft']
print(v['head']['sha'])
