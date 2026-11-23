from pathlib import Path
import subprocess,json,os
from concurrent.futures import ThreadPoolExecutor
z=Path('evidence/hw-locale')
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config'}
def fetch(n):
    p=json.loads(subprocess.check_output(['E:/soundcraft/tools/gh/bin/gh.exe','api',f'repos/storytold/soundcraft/pulls/{n}'],env=env))
    (z/f'{n}-before.json').write_text(json.dumps(p,ensure_ascii=False),encoding='utf8')
    (z/f'{n}-before.md').write_text(p['body'],encoding='utf8')
    print(n,'\n'+'\n'.join([l for l in p['body'].splitlines() if 'head' in l.lower() or 'passed' in l or 'Actions' in l or 'CI:' in l or 'hosted' in l or 'verified' in l.lower()][:15]).encode('ascii','backslashreplace').decode(),flush=True)
with ThreadPoolExecutor() as x:list(x.map(fetch,[1662,1663,1669]))
