## What this PR does

Generate MIDI Time Code or follow a forward source for playback. Session Setup controls frame rate, start, signed offset and Freewheel (None, Frames, Jam Sync). Stopped locates send full-frame position; rolling sends quarter frames. The reader accepts interleaved real-time messages and follows continuous timecode across midnight. Changing the session start with Keep Clips at Their Timecode moves automation when Automation Follows Edit is enabled. Markers and tempo stay in place. Invalid sync settings recover individually with a visible explanation.

## Verification on the exact head

Windows, `e877e96f10cc19c15079975761eb2c724f29a16e`. GitHub Actions on this head: Nix `action_required`, ast-grep `action_required`, CI `action_required`.

| Command | Result |
| --- | --- |
| `cargo test --locked -j 2 -p soundcraft-playback --lib -- --test-threads=2` | 219 passed, 2 ignored |
| `cargo test --locked -j 2 -p soundcraft-ui-egui --lib -- --test-threads=2` | 390 passed |
| `cargo test --locked -j 2 -p soundcraft-engine --lib -- --test-threads=2` | 451 passed, 1 failed (#1536) |
| `cargo test --locked -j 2 -p soundcraft --bin soundcraft -- --test-threads=2` | 58 passed |
| `cargo clippy --locked -j 2 -p soundcraft-playback -p soundcraft-ui-egui --lib --tests --no-deps -- -D warnings` | Passed |
| `cargo fmt --all -- --check` | Passed |

A stopped monitored locate at sample 42,000 formerly published 41,576. The regression now observes 42,000. The audio recovery and output-scheduler fixes also run independently in #1662. The ten inline review threads are resolved. [Formal review](https://github.com/storytold/soundcraft/pull/1663#pullrequestreview-6010501117) · [25 findings and their verification](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074865328).

CodeRabbit reviewed the earlier revision. Automatic draft reviews are skipped. [Draft review status](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7027417714)

Additional pass: `cargo test --locked -p soundcraft-playback --lib matching_rate_with_jitter_never_reports_a_mismatch -- --ignored`. The test covers four wire rates.

[Verification and red/green evidence](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7077796021).

## Hardware status

Model 12 and UM-ONE exercised all six output rates, drop-frame minute/tenth-minute locates, shared-port calibration and cable recovery with None, Frames (8) and Jam Sync. Ten SD recordings had a 42.875 ms onset spread. A controlled replay isolated stale zero output lead; #1662 fixed that path. The three later digital playback measurements differed by 0.140 ms. The ten SD takes have not been repeated since the fix. [Measurements](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)

## Known limits

Forward chase runs on the local audio clock after locating. A subsequent relocation may be audible; Online recording is disabled to avoid moving a take's recording position. Tight continuous alignment can require a shared sample clock. Fractional non-drop and integer rates share MIDI wire codes. One physical Frames (8) reconnection briefly lost lock again. The existing Windows movie relink test is tracked separately by #1536.

## Open questions

None.

## Merge order

#1662 → **#1663** → #1669. Part of #1661. [Review the MTC-only diff](https://github.com/mtlcl410/soundcraft/compare/feat/g11-midi-beat-clock-out...feat/g11-mtc-generate-chase).
