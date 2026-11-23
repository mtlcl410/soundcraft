"""Assemble the MTC verification table from the committed revision."""
from pathlib import Path
import json,sys

d=Path(__file__).resolve().parent
rows=json.loads((Path(sys.argv[1])/'results.json').read_text())
assert len(rows)==6
head=rows[0]['head']
lines=[]
for row in rows:
    r='; '.join(t.removeprefix('test result: ').split('; finished')[0] for t in row['result'])
    if not r:
        r='Passed' if row['code']==0 else f"Failed ({row['code']})"
    lines.append(f"| `{row['command']}` | {r} |")
ignored=Path(sys.argv[1])/'ignored-rate.log'
if ignored.exists() and '1 passed; 0 failed' in ignored.read_text(encoding='utf8'):
    lines.append('| `cargo test --locked -p soundcraft-playback --lib matching_rate_with_jitter_never_reports_a_mismatch -- --ignored` | 1 passed (same compiled test binary). |')
table='\n'.join(lines)
(d/'evidence'/'body1663.md').write_text(f"""## What this PR does

Generate MIDI Time Code or follow a forward source for playback. Session Setup controls frame rate, start, signed offset and Freewheel (None, Frames, Jam Sync). Stopped locates send full-frame position; rolling sends quarter frames. The reader accepts interleaved real-time messages and follows continuous timecode across midnight. Changing the session start with Keep Clips at Their Timecode moves automation when Automation Follows Edit is enabled. Markers and tempo stay in place. Invalid sync settings recover individually with a visible explanation.

## Verification on the exact head

Windows, `{head}`.

| Command | Result |
| --- | --- |
{table}

On the earlier MTC head the pre-roll duration failed at a one-hour session start, a fractional full-frame locate landed one sample early, the generator missed its first quarter-frame group, a stopped offset edit left the cursor behind, and queued Record failed to give the Online refusal reason. Automation also stayed at its original positions. Frame rounding, generator groups, both Record entry paths, marker/tempo invariance and undo are covered in this layer. [Failure and correction evidence]({sys.argv[2]})

## Hardware status

Model 12 and UM-ONE exercised all six output rates, drop-frame minute/tenth-minute locates, shared-port calibration and cable recovery with None, Frames (8) and Jam Sync. Ten SD recordings had a 42.875 ms onset spread. A controlled replay isolated stale zero output lead; #1662 fixed that path. The three later digital playback measurements differed by 0.140 ms. The ten SD takes have not been repeated since the fix. [Measurements](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)

## Known limits

Forward chase runs on the local audio clock after locating. A subsequent relocation may be audible; Online recording is disabled to avoid moving a take's recording position. Tight continuous alignment can require a shared sample clock. Fractional non-drop and integer rates share MIDI wire codes. One physical Frames (8) reconnection briefly lost lock again. The existing Windows movie relink test is tracked separately by #1536.

## Open questions

None for this layer.

## Merge order

#1662 → **#1663** → #1669. Part of #1661. [Review the MTC-only diff](https://github.com/mtlcl410/soundcraft/compare/feat/g11-midi-beat-clock-out...feat/g11-mtc-generate-chase).
""",encoding='utf8')
