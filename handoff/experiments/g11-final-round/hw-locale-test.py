from pathlib import Path
import json,os,subprocess,re
d=Path(__file__).resolve().parent
z=d/'evidence'/'hw-locale'
z.mkdir(exist_ok=True)
rows=[]
for tree,n,target in [('beat',1662,'g11-r3-redgreen-1662-target'),('mtc',1663,'g11-review3-mtc-fix-target'),('follow',1669,'g11-verify-beat-target')]:
    w=d/tree
    def git(*argv):return subprocess.check_output(['git',*argv],cwd=w).decode().strip()
    head=git('rev-parse','HEAD')
    assert not git('status','--porcelain')
    assert not git('diff','58061298','--','crates/ui-egui/locales/pt-BR/mod.rs')
    env=os.environ|{'CARGO_TARGET_DIR':str(d.parent/target),'CARGO_TERM_COLOR':'never'}
    cmds=[['fmt','--all','--','--check'],['test','--locked','-j','2','-p','soundcraft-ui-egui','--lib','--','--test-threads=2','localization::tests::','every_preference_text_has_a_portuguese_translation']]
    for a in cmds:
        out=z/f'{n}-{head[:8]}-{a[0]}.log'
        with out.open('wb') as f:rc=subprocess.run(['cmd','/c',str(d.parent/'g11-a10-recovery'/'run.cmd'),*a],cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
        t=out.read_text(encoding='utf8',errors='replace')
        if a[0]=='test' and (not all(any(l.startswith('test ') and name in l and l.endswith(' ... ok') for l in t.splitlines()) for name in ['beat_clock_uses_the_catalog','localized_source_strings_have_catalog','every_preference_text_has_a_portuguese_translation'])): rc=1
        assert git('rev-parse','HEAD')==head and not git('status','--porcelain')
        rows.append(dict(pr=n,head=head,command='cargo '+' '.join(a),code=rc,result=[line for line in t.splitlines() if line.startswith('test result:')]))
        print(rows[-1],flush=True)
        (z/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
        if rc:raise SystemExit(rc)

