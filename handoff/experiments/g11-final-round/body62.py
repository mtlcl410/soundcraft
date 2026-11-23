"""Prepare the Beat Clock description using the head's saved test output."""
from pathlib import Path
import json,sys

d=Path(__file__).resolve().parent
folder=Path(sys.argv[1])
rows=json.loads((folder/'results.json').read_text(encoding='utf8'))
res={r['check']:r for r in rows}
assert len(rows)==5
sha=rows[0]['head']
def result(k):
    r=res[k]
    return '<br>'.join(item.removeprefix('test result: ').split('; finished')[0] for item in r['result']) or ('Passed' if r['code']==0 else f"Failed ({r['code']})")
table='\n'.join('| `'+r['command']+'` | '+result(r['check'])+' |' for r in rows)
(d/'evidence'/'body1662.md').write_text(f"""## What this PR does

Send Beat Clock, transport and Song Position Pointer to selected MIDI outputs. A stopped locate sends one SPP immediately. After an output timing interruption, repay missing clocks evenly within one quarter note. Each destination has its own ±250 ms calibration. Duplicate port names have numbered destinations; a known device remains bound to its saved endpoint. Warnings require a route using device compensation. A damaged preference resets individually and is identified at startup.

The scheduler uses the `craft-midi-sync` alias at `08da5e14` (MIT OR Apache-2.0) alongside the existing `craft-midi` revision to obtain the sync message API. `thread-priority 3.1.1` (MIT) raises the output worker priority where supported. Both licenses satisfy the project allowlist.

## Verification on the exact head

Windows, `{sha}`. [Test evidence]({sys.argv[2]})

| Command | Result |
| --- | --- |
{table}

Before the fixes the stopped seek emitted only Stop, the second same-name output was unavailable, an unused route raised a timing warning, and enumeration ran eight times in a minute after the retry budget expired. A poisoned graph returned silence, Notes/Controllers remained editable, and one malformed MIDI setting rejected the saved UI state.

## Hardware status

Earlier Model 12 USB MIDI → DIN → UM-ONE tests verified 20/20 idle starts, 5/5 minimized starts and 20/20 loop-end stops at 480 frames. The −200-sample setting advanced clock arrivals by 4.268/4.071 ms at 120/180 BPM. Physical duplicate-output recovery, 256-frame stop and acoustic alignment remain unverified. Optional loopback: set `SOUNDCRAFT_LOOPBACK_IN` and `SOUNDCRAFT_LOOPBACK_OUT`, then run `cargo test -p soundcraft-playback --lib beat_clock_reaches_a_virtual_midi_receiver -- --ignored --nocapture`. [Hardware evidence](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)

## Known limits

Exclusive audio backends require manual Reconnect. Live plug-in delay changes take effect on the next rendered session revision. Already delivered MIDI retains its timing. Notes/Controllers compensation becomes available when external MIDI track output is supported.

## Open questions

None.

## Merge order

Merge #1662, then #1663, then #1669. #1536 handles independent Windows checks. Part of #1661.
""",encoding='utf8')
