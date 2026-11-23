## What this PR does

Generate MIDI Time Code or follow a forward source for playback. Session Setup controls frame rate, start, signed offset and Freewheel (None, Frames, Jam Sync). Stopped locates send full-frame position; rolling sends quarter frames. The reader accepts interleaved real-time messages and follows continuous timecode across midnight. Changing the session start with Keep Clips at Their Timecode moves automation when Automation Follows Edit is enabled. Markers and tempo stay in place. Invalid sync settings recover individually with a visible explanation.

## Verification on the exact head

Windows, `8161383751314c94644a4d2af759347eddfbecc6`.

| Command | Result |
| --- | --- |
| `cargo test --locked -j 2 -p soundcraft-playback --lib -- --test-threads=2` | ok. 219 passed; 0 failed; 2 ignored; 0 measured; 0 filtered out |
| `cargo test --locked -j 2 -p soundcraft-ui-egui --lib -- --test-threads=2` | ok. 390 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out |
| `cargo test --locked -j 2 -p soundcraft-engine --lib -- --test-threads=2` | FAILED. 451 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out |
| `cargo test --locked -j 2 -p soundcraft --bin soundcraft -- --test-threads=2` | ok. 58 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out |
| `cargo clippy --locked -j 2 -p soundcraft-playback -p soundcraft-ui-egui --lib --tests --no-deps -- -D warnings` | Passed |
| `cargo fmt --all -- --check` | Passed |
| `cargo test --locked -p soundcraft-playback --lib matching_rate_with_jitter_never_reports_a_mismatch -- --ignored` | 1 passed (same compiled test binary). |

On the earlier MTC head the pre-roll duration failed at a one-hour session start, a fractional full-frame locate landed one sample early, the generator missed its first quarter-frame group, a stopped offset edit left the cursor behind, and queued Record failed to give the Online refusal reason. Automation also stayed at its original positions. Frame rounding, generator groups, both Record entry paths, marker/tempo invariance and undo are covered in this layer. [Failure and correction evidence](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074865328)

CI, Nix, SonarCloud and ast-grep all require maintainer approval on this head. [Formal review](https://github.com/storytold/soundcraft/pull/1663#pullrequestreview-6010501117) and [25-item resolution](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074865328).

CodeRabbit reviewed the preceding revision. The latest head has not been reviewed by CodeRabbit because automatic draft reviews are skipped. [Draft review status](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7027417714)

## Hardware status

Model 12 and UM-ONE exercised all six output rates, drop-frame minute/tenth-minute locates, shared-port calibration and cable recovery with None, Frames (8) and Jam Sync. Ten SD recordings had a 42.875 ms onset spread. A controlled replay isolated stale zero output lead; #1662 fixed that path. The three later digital playback measurements differed by 0.140 ms. The ten SD takes have not been repeated since the fix. [Measurements](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)

## Known limits

Forward chase runs on the local audio clock after locating. A subsequent relocation may be audible; Online recording is disabled to avoid moving a take's recording position. Tight continuous alignment can require a shared sample clock. Fractional non-drop and integer rates share MIDI wire codes. One physical Frames (8) reconnection briefly lost lock again. The existing Windows movie relink test is tracked separately by #1536.

## Open questions

None for this layer.

## Merge order

#1662 → **#1663** → #1669. Part of #1661. [Review the MTC-only diff](https://github.com/mtlcl410/soundcraft/compare/feat/g11-midi-beat-clock-out...feat/g11-mtc-generate-chase).

