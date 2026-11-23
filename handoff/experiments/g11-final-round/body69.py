"""Write #1669's six-section review body, using the exact checks and evidence-comment URL."""
import json
import re
import sys
from pathlib import Path
d=Path(__file__).resolve().parent
folder=Path(sys.argv[1]).resolve()
url=sys.argv[2]
preview=url=='--preview'
if preview:
    url='the-verified-head-evidence-comment'
else:
    assert re.fullmatch(r'https://github.com/storytold/soundcraft/pull/1669#issuecomment-\d+',url)
metrics=json.loads((folder/'review-metrics.json').read_text(encoding='utf8'))
head=metrics['head']
rows=json.loads((folder/'results.json').read_text(encoding='utf8')) if (folder/'results.json').exists() else []
assert preview or (len(rows)==7 and all(row['head']==head for row in rows))
profiles=json.loads((folder/'profiles.json').read_text(encoding='utf8'))
assert len(profiles)==13 and all(p['head']==head and p['code']==0 for p in profiles)
bt=chr(96)
def inline(s):
    return bt+s+bt
def result(row):
    if not row['result']:
        return 'Pass' if row['code']==0 else 'Fail'
    parts=[]
    for line in row['result']:
        mt=re.search(r'(\d+) passed; (\d+) failed; (\d+) ignored',line)
        assert mt, line
        a,b,c=mt.groups()
        parts.append(f'{a} passed'+(f', {b} failed (#1536)' if b!='0' else '')+(f', {c} ignored' if c!='0' else ''))
    return ' / '.join(parts)
table='\n'.join('| '+inline(r['command'])+' | '+result(r)+' |' for r in rows)
if len(rows)!=7:
    table+='\n| Exact suite | Local results pending |'
optnames=[p['name'] for p in profiles if p['ignored']]
opts=', '.join("'"+s+"'" for s in optnames)
opt_command=f"@({opts}) | ForEach-Object {{ cargo test --locked -p soundcraft-ui-egui --lib $_ -- --ignored --nocapture --test-threads=1 }}"
body=f"""## What this PR does

Follow an external MIDI Beat Clock for playback and recording. EXT shows Waiting, Locked or Coasting. Coast keeps an open take running and relocks on F8 alone; Stop on loss finishes the take. External position overrides the local loop, rolling SPP is ignored, and Stop releases held notes before resetting instruments. The tempo response is fixed. Invalid follow settings recover field by field with a visible notice. Fixes #1674 and #1675.

Audio and MIDI can record because the beat grid follows the incoming Clock. In MTC Online (#1663), an absolute locate could displace an open take. Pro Tools documents Clock transmission on pp. 743–744; the MPC guide disables audio recording while receiving Clock. The audio/MIDI tests are {inline('coast_keeps_the_audio_and_midi_take_through_clock_loss_and_continue')} and {inline('stop_on_clock_loss_commits_the_audio_and_midi_take')}. [Pro Tools 2026.4](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf) · [MPC v3.5, p. 60](https://cdn.inmusicbrands.com/Software/SME0-3.5.0/Public/MPC%20Standalone%20OS%20-%20User%20Guide%20-%20v3.5.pdf#page=60)

## Verification on the exact head

Windows, {inline(head)}. {metrics['ci']}

| Command | Result |
|---|---|
{table}

Six opt-in controls also passed. Reproduce them in PowerShell:

~~~powershell
{opt_command}
~~~

The old follower lost clock through a genuine brake and missed exact ±8% changes in all 20 original trials; stale clip identity changed a 24,000-sample length to 48,000. {metrics['dj']} {metrics['history']}  [Verification evidence]({url})

## Hardware status

TASCAM Model 12 → Roland UM-ONE with S-MU2000: one crash from 8.000 s, none from 8.125 s, and all eight snares at 100 and 120 BPM on MAIN. The new DJ profiles use simulated Clock and rendered PCM. Akai MPC hardware remains untested. [Hardware measurements](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)

## Known limits

{metrics['burst']} A locked, steady source predicts only to the device deadline. {metrics['deadline']} For live use, try 64–256 frames where supported. #1686 tracks one unexplained difference in twelve 256-frame takes. A separate 64-frame capture had 40 near-silent samples.

## Open questions

- Which shortcut should toggle EXT?
- Is the clock-loss boundary suitable live? Steady fast clock uses 150 ms. A slowing source can extend this to 1.5 s. Active Sensing times out at 300 ms without MIDI activity.
- What should the Setup › MIDI › Sync entry be called?
- Should MTC chase apply its reader port’s input offset?

## Merge order

#1662 → #1663 → **#1669**. Part of #1661. [Review just this layer](https://github.com/mtlcl410/soundcraft/compare/feat/g11-mtc-generate-chase...feat/g11-external-clock-follow).
"""
outfile=d/'evidence'/('body1669-preview.md' if preview else 'body1669.md')
outfile.write_text(body,encoding='utf8')
print(outfile,len(body))

