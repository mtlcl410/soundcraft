"""Fast-forward an existing PR branch or publish its verified body and evidence."""
from pathlib import Path
import json,os,subprocess,sys

d=Path(__file__).resolve().parent
ev=d/'evidence'
n,tree,action=sys.argv[1:]
w=d/tree
gh='E:/soundcraft/tools/gh/bin/gh.exe'
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config','GIT_TERMINAL_PROMPT':'0'}
def run(args, directory=w, body=None):
    return subprocess.run(args,cwd=directory,env=env,input=body,capture_output=True,check=True).stdout.decode('utf8')
def api(endpoint,*args,payload=None):
    argv=[gh,'api',endpoint,*args]
    if payload is not None:
        argv.extend(['--input','-'])
    return json.loads(run(argv,body=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf8')))
repo='repos/storytold/soundcraft'
pr=f'{repo}/pulls/{n}'
before=json.loads((ev/f'before-{n}.json').read_text(encoding='utf-8-sig'))
head=run(['git','rev-parse','HEAD']).strip()
remote=api(pr)
ref=remote['head']['ref']
assert remote['head']['repo']['full_name']=='mtlcl410/soundcraft' and ref==before['head']['ref']
assert not run(['git','status','--porcelain']).strip()
results=ev/f'{n}-{head[:8]}'/'results.json'
rows=json.loads(results.read_text())
assert rows and all(r['head']==head for r in rows)
assert any(r['check']=='fmt' and r['code']==0 for r in rows)
required_tests={
    '1662':{'soundcraft-playback':['stopped_locates_announce','duplicate_calibrations_follow'],'soundcraft-ui-egui':['midi_sync_pref_notes_compensation'],'soundcraft':['midi_sync_pref_']},
    '1663':{'soundcraft-playback':['framing_generator_and_chase','mtc_sync_route_warns','first_integer_sample_of_an_even','full_frame_locate_matches'],'soundcraft-ui-egui':['online_service_reports','offset_edit_repositions','mtc_sync_route_keeps'],'soundcraft-engine':['timecode_retention_respects','timecode_labels_for_session','mtc_bad_'],'soundcraft':['mtc_bad_workstation_fields']}
}
for label,names in required_tests.get(n,{}).items():
    lines=(results.parent/(label+'.log')).read_text(encoding='utf8').splitlines()
    for name in names:
        assert any(name in line and line.startswith('test ') and line.endswith(' ... ok') for line in lines),(label,name)
for r in rows:
    if r['code']==0:
        continue
    log=(results.parent/(r['check']+'.log')).read_text(encoding='utf8')
    failed=[x for x in log.splitlines() if x.startswith('test ') and x.endswith(' ... FAILED')]
    assert r['check']=='soundcraft-engine' and failed==['test io::session::open_tests::each_movie_is_kept_relinked_or_offline ... FAILED'],(r,failed)
if action=='push':
    if remote['head']['sha']==head:
        print('Already pushed',head)
        raise SystemExit(0)
    previous=remote['head']['sha']
    if previous!=before['head']['sha']:
        prior=ev/f'{n}-{previous[:8]}'/'published.json'
        assert prior.is_file() and json.loads(prior.read_text())['head']==previous,previous
    run(['git','merge-base','--is-ancestor',remote['head']['sha'],head])
    print(run(['git','-c','credential.helper=','-c','credential.helper=!E:/soundcraft/tools/gh/bin/gh.exe auth git-credential','push','https://github.com/mtlcl410/soundcraft.git',f'HEAD:refs/heads/{ref}']))
    import time
    for _ in range(30):
        if api(pr)['head']['sha']==head:break
        time.sleep(2)
    assert api(pr)['head']['sha']==head
    (results.parent/'published.json').write_text(json.dumps({'head':head,'branch':ref}),encoding='utf8')
elif action=='evidence':
    assert remote['head']['sha']==head
    f=ev/f'comment-{n}.md'
    body=f.read_text(encoding='utf8')
    assert head in body
    url=api(f'{repo}/issues/{n}/comments','-X','POST',payload={'body':body})['html_url']
    (ev/f'comment-{n}-url.txt').write_text(url)
    print(url)
elif action=='body':
    assert remote['head']['sha']==head
    body=(ev/f'body{n}.md').read_text(encoding='utf8')
    assert head in body
    print(api(pr,'-X','PATCH',payload={'body':body})['html_url'])
else:
    raise SystemExit('Unknown action')
