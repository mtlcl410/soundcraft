## What this PR does

**Setup › MIDI › Sync** can follow a sequencer, an MPC or a third-party Link-to-MIDI-clock bridge. SoundCraft follows the incoming 24 PPQN tempo and transport. This extends the MIDI Beat Clock workflow in the Pro Tools Reference Guide 2026.4, pp. 743–744, which documents sending clock.

Start selects song zero and rolls on the next clock. Continue resumes, a stopped Song Position Pointer selects a six-clock (sixteenth-note) position, and Stop ends playback. The transport estimates tempo on a transient beat grid; the saved session tempo map is preserved. Audio and MIDI recording are available during Beat Clock follow. Each input has a workstation calibration in samples.

On clock loss, the default is to coast at the last tempo. Stop-on-loss is also available. A new Start/Continue rearms the follower. Setup rejects simultaneous MTC chase and Beat Clock follow and prevents sending clock to the followed port. The diagnostic command reports state, BPM, jitter, phase error and dropout count.

## Shared code

This depends on #1663's timestamp mapping and windowed pulse estimator and #1662's presentation clock and sync status. The input path coalesces clock pulses and bounds queued transport transitions. Tempo changes affect the playback grid without resampling the audio. The user guide includes routing an external sequencer and an independently installed Link bridge.

## How it was verified

- A simulated sender covers 90, 120 and 174 BPM, Gaussian timestamp jitter of 0.5, 2 and 4 ms and USB-like timestamp batching. At 120 BPM and 2 ms jitter, the steady-state displayed tempo stays within ±0.05 BPM. The tempo-step test reaches 150 BPM within 0.1 BPM after 24 clocks from 120 BPM; a separate ramp exercises continuous changes.
- `start_continue_spp_stop_and_realtime_inside_sysex` and `coast_or_stop_once_on_loss_and_resume_only_after_transport` exercise transport ordering and both loss policies. A 50,000-byte deterministic noise stream checks that no spurious Play occurs without Start/Continue.
- The recording regression `external_clock_take_uses_transient_grid_and_keeps_the_document_tempo` failed when the original session grid was used for the recorded take. Regressions were also exercised with deliberately broken transport mapping and tempo estimation.

- Continue from sample 72,000 in a project with a prior 120-to-60 BPM tempo change failed before the fix. Following now preserves the score before the insertion, applies the external tempo from there, and resumes at the requested sample. A separate ownership regression exercises a full or disconnected retirement channel so an audio callback can hand off an old session without destroying it in real time.
- Windows library tests: 146 playback tests and 356 desktop UI tests passed; three opt-in playback tests were skipped. The recorded-take, variable-tempo Continue and snapshot-retirement regressions passed. The recording test originally wrote 1,280 ticks; the corrected take has 960 ticks per quarter and preserves the saved tempo map. A local baseline run confirmed the independent Windows AAF failure tracked by #1658.

Final Windows integration gate: `cargo xtask ci` passed for feature head `c78576b` plus #1536 and #1658. Cargo reported 1,950 passing tests across all targets and doctests. The gate includes workspace Clippy with warnings denied and the WebAssembly app build.

## Hardware status

Not yet verified on hardware; a hardware check is planned once all three PRs are final (see #1661).

## Known limits and deferred work

The project tempo map cannot yet be written from incoming clock as a tempo-record pass. Bridge software is supplied by the user. Continuous MTC chase, MMC, a loopback calibration assistant, OS-timestamped sends and Windows MIDI Services remain separate work.

## Review and merge order

#1536 → #1662 → #1663 → **#1669**. The prerequisite branches live on the contributor fork. Review the [clock-follow increment over #1663](https://github.com/mtlcl410/soundcraft/compare/feat/g11-mtc-generate-chase...feat/g11-external-clock-follow). Refresh this draft from main after #1663 lands. Tracks #1661.
