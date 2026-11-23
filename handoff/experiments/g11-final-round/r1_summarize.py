from pathlib import Path
import json,re
d=Path(__file__).resolve().parent/'evidence'
r=d/'r1-1662-red'
g=d/'1662-56169122'
out=json.loads((r/'results.json').read_text())
checks=json.loads((g/'results.json').read_text())
assert len(checks)==5 and all(c['code']==0 for c in checks),checks
assert all(row['outcome']=='FAILED' for row in out['cases'])
log=(r/'red.log').read_text(encoding='utf8',errors='replace')
greens='\n'.join((g/(c['check']+'.log')).read_text(encoding='utf8',errors='replace') for c in checks[:2])
out['base']='7ff81296df6d36a565c4636d75da682d52bc5423'
out['head']=checks[0]['head']
for row in out['cases']:
    name=re.escape(row['test'])
    assert re.search(r'test [^\n]*'+name+r' \.\.\. ok', greens), name
    row['head_result']='ok'
    msg=re.search(r'---- [^\n]*'+name+r' stdout ----\n+(.*?)(?:\n\n|\Z)',log,re.S)
    if msg: row['old_failure']=msg.group(1)
out['head_checks']=checks
(g/'r1-regressions.json').write_text(json.dumps(out,indent=2),encoding='utf8')
lines=['# R-1 — Beat Clock output, independent lower-layer verification','',
       'The four repairs and their regression tests were moved to #1662. The MTC-only output fixture remains in #1663. The MTC merge preserves each fix once.','',
       'The lower base was '+out['base']+'. Its [test-only changes](../r1-1662-red/lower-head-with-probes.patch) adapt test signatures to the earlier implementation. The production transport and recovery logic on the red worktree is the original code.','',
       'For item 19, the implementation was already correct on the lower base. To prove the strengthened assertion distinguishes destinations, the negative control swaps the two queued route indices. The distinguishable F1/F8 packets make the mutant fail.','',
       '| CodeRabbit item | Regression | On pre-fix base or mutation | On '+out['head'][:8]+' |','|---:|---|---|---|']
for row in out['cases']:
    lines.append(f"| {row['finding']} | \x60{row['test']}\x60 | {'Wrong route rejected (mutation)' if row['finding']==19 else 'Failed as expected'} | Passed |")
lines+=['','[All assertion failures](../r1-1662-red/red.log) · [Commands and machine-readable measurements](r1-regressions.json) · [Exact-head verification](results.json)']
(g/'r1-regressions.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(out['head'],[(c['check'],c['result']) for c in checks])
