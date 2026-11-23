import subprocess,os,time,json,re,sys
from pathlib import Path
d=Path(__file__).resolve().parent
root=d/'publish'
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config','GH_PROMPT_DISABLED':'1','PYTHONUTF8':'1'}
gh='E:/soundcraft/tools/gh/bin/gh.exe'
for name,pattern in [('release-sweep.log','test result: ok. 1 passed'),('validated-integrated-a4.log','test result: ok. 1 passed'),('release-clippy.log','Finished `dev` profile')]:
 deadline=time.monotonic()+600
 while time.monotonic()<deadline:
    data=(d/name).read_text(encoding='utf-8-sig',errors='replace') if (d/name).exists() else ''
    if 'test result: FAILED' in data or re.search(r'^error',data,re.M):sys.exit('gate failed: '+name)
    if pattern in data:break
    time.sleep(4)
 else:sys.exit('pending gate: '+name)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
previous=subprocess.check_output(['git','rev-parse','HEAD^'],cwd=root).decode().strip()
info=json.loads(subprocess.check_output([gh,'api','repos/storytold/soundcraft/pulls/1669'],env=env))
assert info['draft'] and previous.startswith('af4af80') and info['head']['sha']==previous and info['head']['repo']['full_name']=='mtlcl410/soundcraft'
subprocess.run(['git','-c','credential.helper=','-c',f'credential.helper=!{gh} auth git-credential','push','https://github.com/mtlcl410/soundcraft.git','HEAD:refs/heads/feat/g11-external-clock-follow'],env=env,cwd=root,check=True)
subprocess.run([sys.executable,str(d/'publish-description.py'),'--apply'],cwd=d,env=env,check=True)
info=json.loads(subprocess.check_output([gh,'api','repos/storytold/soundcraft/pulls/1669'],env=env))
assert info['head']['sha']==head and info['draft'] and head+'/docs/external-clock-response-measurements.md' in info['body']
print('verified',head)
