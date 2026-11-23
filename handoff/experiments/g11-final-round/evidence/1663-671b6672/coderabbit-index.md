# #1663 CodeRabbit review of 671b6672

[Formal review](https://github.com/storytold/soundcraft/pull/1663#pullrequestreview-6010501117). Ten inline major findings, fourteen minor findings and one documentation nit.

## Major

| File | Comment |
|---|---|
| `crates/playback/src/callback.rs:856` | [Consume a pending tail at the rate at which it was rendered.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776421) |
| `crates/playback/src/callback.rs:859` | [Publish the actual playhead position while stopped.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776425) |
| `crates/playback/src/midi.rs:397` | [Stamp channel events while `writers` is held.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776429) |
| `crates/playback/src/mtc_input.rs:58` | [Preserve the reader day when a short dropout crosses midnight.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776431) |
| `crates/playback/src/stream_recovery.rs:271` | [Recheck the original render fault under the graph lock.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776437) |
| `crates/playback/src/sync_clock.rs:184` | [Do not encode an old presentation with the latest session.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776442) |
| `crates/playback/src/sync_output.rs:438` | [Discard queued position packets when their transport pass is superseded.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776444) |
| `crates/playback/src/sync_output.rs:486` | [Retry a transport Stop that fails during MIDI handoff.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776446) |
| `crates/ui-egui/src/app/audio.rs:39` | [Discard the old recovery target when Apply changes the output.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776453) |
| `crates/ui-egui/src/app/midi.rs:131` | [Require a player before starting a MIDI-only recording.](https://github.com/storytold/soundcraft/pull/1663#discussion_r4656776454) |

## Additional items in the review body

| File | Comment |
|---|---|
| `crates/engine/src/cmd/options.rs` | Remove the legacy offset after an explicit offset change. |
| `crates/ui-egui/src/app/files.rs` | Preserve the conflict warning after recovery. |
| `docs/midi-input.md` | State that external MIDI Beat Clock following is unavailable. |
| `crates/playback/src/sync_output.rs` | Use the callback's sample rate for its reported mixer delay. |
| `crates/playback/src/sync_output/ports.rs` | Count unnameable ports when detecting duplicate IDs. |
| `crates/playback/src/callback.rs` | A refused record start leaves its pass pending, so MIDI keeps being recorded while playback runs. |
| `crates/playback/src/beat_clock.rs` | Do not emit two MIDI clocks in the launch batch. |
| `crates/playback/src/beat_clock.rs` | Keep the SPP range warning until the stopped position changes. |
| `crates/playback/src/sync_output_tests.rs` | Use distinct packets to verify which route survives the timing gap. |
| `crates/playback/src/beat_clock/recovery.rs` | Exit repayment when a worker stall makes the window obsolete. |
| `crates/playback/src/midi.rs` | Notify the host after releasing `writers`. |
| `crates/ui-egui/src/app/audio.rs` | Clear the idle warning after a successful manual reconnect. |
| `crates/playback/src/stream_recovery.rs` | Allow a later probe if the endpoint stays present. |
| `crates/playback/src/stream.rs` | Reconnect cannot reuse an output that the original open chose from a fallback audio system. |
| `crates/dsp/src/offline.rs` | Document the public helper’s callback contract. |
