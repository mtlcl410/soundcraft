# #1662 file inventory

Compared with upstream main by three-dot diff. 34 paths before packaging and 33 afterwards. Embedded unit tests are listed with their product file. No changes to audio, MIDI or application behavior in the packaging commit.

## Product code (23)

| Path | Purpose |
| --- | --- |
| `crates/engine/src/cmd/setup_more.rs` | Register desktop Beat Clock setup and sync diagnostics commands; report headless availability. |
| `crates/model/src/lib.rs` | Export the legacy Beat Clock configuration reader. |
| `crates/model/src/midi_beat_clock.rs` | Read the previous session flag, destination and offset for migration to machine preferences. |
| `crates/playback/src/beat_clock.rs` | Encode and schedule Beat Clock, Start, Continue, Stop, SPP and loop transitions. |
| `crates/playback/src/beat_clock/recovery.rs` | Repay ticks missed during loss of audio-output timing. |
| `crates/playback/src/callback.rs` | Publish rendered audio position, presentation timing and delay compensation. |
| `crates/playback/src/lib.rs` | Expose player sync routing, transport wakeups, timing status and output recovery. |
| `crates/playback/src/stream.rs` | Connect native audio stream timestamps, invalidation and stopped-device recovery to playback. |
| `crates/playback/src/stream_recovery.rs` | Gate replacement of an invalid shared-WASAPI stream using fresh device timestamps; includes deterministic tests. |
| `crates/playback/src/sync_clock.rs` | Represent presentation timing, revisions and loop position for MIDI scheduling. |
| `crates/playback/src/sync_output.rs` | Manage the output worker, per-port connections, delivery queues, priorities and recovery. |
| `crates/playback/src/sync_status.rs` | Report port timing, errors, output lead and diagnostics. |
| `crates/ui-egui/locales/pt-BR/mod.rs` | Translate Beat Clock, timing and external-device preference labels. |
| `crates/ui-egui/src/app.rs` | Initialize and service MIDI synchronization in the UI update loop. |
| `crates/ui-egui/src/app/audio.rs` | Apply audio/sync settings, show output failures and gate reconnection. |
| `crates/ui-egui/src/app/files.rs` | Check legacy calibration when a project is loaded. |
| `crates/ui-egui/src/dialogs.rs` | Register and exercise the Beat Clock dialog, including long port lists. |
| `crates/ui-egui/src/dialogs/midi_beat_clock.rs` | Edit selected destinations and signed sample offsets. |
| `crates/ui-egui/src/lib.rs` | Store UI, preference migration and output recovery state. |
| `crates/ui-egui/src/menus.rs` | Expose Setup › MIDI Beat Clock and handle its action. |
| `crates/ui-egui/src/midi_sync.rs` | Persist, validate and migrate machine-specific ports, offsets and compensation. |
| `crates/ui-egui/src/panels/windows.rs` | Gate the playback engine reconnect action when transport is active. |
| `crates/ui-egui/src/preferences.rs` | Expose external-device delay compensation preferences. |

## CI regression tests (2)

| Path | Purpose |
| --- | --- |
| `crates/playback/src/sync_output_tests.rs` | Deterministic timing, buffering, multiport delivery, retry and counted-tick recovery. Also contains the opt-in OS-port smoke test, which requires an available driver. |
| `crates/playback/src/tests.rs` | Playback callback regressions for compensation, stale or failed output, session revisions and loops. |

## User and project documentation (5)

| Path | Purpose |
| --- | --- |
| `ROADMAP.md` | Record Beat Clock output availability and distinguish remaining MIDI track output work. |
| `docs/roadmap.md` | Distinguish the MIDI-device backlog from G-11 sync features. |
| `docs/gaps.md` | Mark Beat Clock output available and list other sync gaps individually. |
| `docs/hardware-parity.md` | Document supported Clock output routing and Windows wire verification. |
| `docs/midi-input.md` | Explain Beat Clock destinations, calibration, compensation and the setup command. |

## Measurements, images or data (1 before, 0 after)

`crates/playback/src/sync_timing_test.rs` was removed. Its once-off host percentile/load measurement was archived outside the PR. The device loopback test retained its assertions, name and ignored status in `sync_output_tests.rs`.

## Other (3)

| Path | Purpose |
| --- | --- |
| `Cargo.toml` | Alias the `08da5e14` revision of `craft-midi` as `craft-midi-sync` to use sync encoders missing from the original `45a8e166` revision without migrating the other workspace crates. |
| `crates/playback/Cargo.toml` | Use `craft-midi-sync` for native MIDI transport messages and `thread-priority` 3.1.1 for best-effort output-worker scheduling. |
| `Cargo.lock` | Resolve the second `craft-midi` 0.1.0 revision and `thread-priority` 3.1.1. The sync revision uses existing `thiserror` 2.0.21. The priority crate reuses existing `bitflags`, `cfg-if`, `libc`, `log`, `rustversion` and `windows` packages. Existing `craft-scraft-format` and `soundcraft-midi` entries now identify their original `craft-midi` source explicitly; their version and source are unchanged. |
