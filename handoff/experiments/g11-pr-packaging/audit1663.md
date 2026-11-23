# #1663 layered file inventory

Base is the packaged #1662 head. Product files containing inline tests are listed once under their primary role.

## Product code (33)

- `crates/dsp/src/offline.rs` — Expose the existing sample-overlap search routine under its descriptive public name.
- `crates/engine/src/cmd.rs` — Distinguish elapsed minutes/seconds from absolute labels and reject labels before session start.
- `crates/engine/src/cmd/file.rs` — Use the one-hour session origin when creating or closing sessions.
- `crates/engine/src/cmd/options.rs` — Apply session start, external offset, clip-move and Freewheel settings with inline regressions.
- `crates/engine/src/cmd/setup_more.rs` — Share signed timecode offset validation and formatting across Setup commands.
- `crates/engine/src/demo.rs` — Use the new-session constructor for the demo.
- `crates/engine/src/lib.rs` — Initialize session origins and migrate saved offsets and Freewheel modes.
- `crates/playback/src/callback.rs` — Drive chase transport in the audio callback, protect the locate onset and detect drift at the presentation position.
- `crates/playback/src/lib.rs` — Expose encoder and chase operations to the application and register synchronization modules.
- `crates/playback/src/midi.rs` — Timestamp and route the selected MTC input and wake transport on transitions.
- `crates/playback/src/mtc.rs` — Encode stopped full-frame locates and rolling quarter-frame groups in session timecode.
- `crates/playback/src/mtc_input.rs` — Decode and track incoming timecode, rate mismatches, loss and Freewheel. Contains inline reader regressions and the ignored ten-minute-per-rate check.
- `crates/playback/src/sync_input.rs` — Fit pulse timestamps in a bounded window for tempo, phase and jitter estimation.
- `crates/playback/src/sync_output.rs` — Register an additional encoder on the shared worker and coalesce transport wakeups.
- `crates/ui-egui/locales/pt-BR/mod.rs` — Localize MTC setup, status, controls and warnings into Brazilian Portuguese.
- `crates/ui-egui/src/app.rs` — Initialize MTC UI state and service the reader and generator from the app.
- `crates/ui-egui/src/app/audio.rs` — Reapply MTC output after stream changes and protect an acquiring transport from reconnects; includes a stopped-locate regression.
- `crates/ui-egui/src/app/commands.rs` — Display the reason for rejecting the Record command while MTC Online is enabled.
- `crates/ui-egui/src/app/files.rs` — Warn when a loaded session has conflicting legacy offsets.
- `crates/ui-egui/src/app/midi.rs` — Keep MIDI input available for the Online reader and connect its feed to playback.
- `crates/ui-egui/src/app/mtc.rs` — Drive reader/chase commands, freewheel, source selection, rate warnings and diagnostics with integration-style UI tests.
- `crates/ui-egui/src/app/mtc_output.rs` — Validate and restore generator routes, retry rejected updates and share the device calibration with Beat Clock.
- `crates/ui-egui/src/app/playback.rs` — Schedule playback from the chase locate and pass stopped cursor moves to the generator.
- `crates/ui-egui/src/dialogs.rs` — Open and validate Session Setup, synchronization, offset and editable counter dialogs.
- `crates/ui-egui/src/dialogs/midi_beat_clock.rs` — Reuse the shared device offset edit field in the Beat Clock dialog.
- `crates/ui-egui/src/dialogs/session_setup.rs` — Edit the session origin, external offset, rate and Freewheel and capture received timecode.
- `crates/ui-egui/src/dialogs/spot.rs` — Validate absolute Spot input against session start.
- `crates/ui-egui/src/lib.rs` — Hold workstation ports, Gen MTC preferences and runtime chase state.
- `crates/ui-egui/src/menus.rs` — Expose MTC setup, transport and synchronization menu actions.
- `crates/ui-egui/src/midi_sync.rs` — Publish reader and output state through synchronization status.
- `crates/ui-egui/src/panels/transport.rs` — Expose the reader/generator controls in the transport panel.
- `crates/ui-egui/src/panels/windows.rs` — Add access to synchronization within the peripherals panel.
- `crates/ui-egui/src/toolbar.rs` — Open position and selection entry from timeline counters.

## CI tests (6)

- `crates/engine/src/cmd/file/tests.rs` — Qualify the default model session in the file-command fixture.
- `crates/engine/tests/it/min_secs_with_timecode_counter.rs` — Exercise elapsed selection entry with an absolute timecode main counter.
- `crates/playback/src/mtc/tests.rs` — Test generator cadence, drop-frame labels, drift, Freewheel, recording guards and transport races.
- `crates/playback/src/mtc_sync_output_tests.rs` — Verify shared ports, output compensation, generation changes, timing recovery and generator-to-reader agreement. Retains deterministic worker tests.
- `crates/playback/src/sync_output_tests.rs` — Share the simulated presentation block constructor with MTC worker regressions.
- `crates/ui-egui/tests/it/sub_counter.rs` — Validate main-counter rejection of pre-session absolute labels.

## User documentation (5)

- `ROADMAP.md` — Add the MTC-specific progress entry.
- `docs/gaps.md` — Document MTC delivery and its Online record restriction independently of Beat Clock.
- `docs/hardware-parity.md` — Update the MTC generation/chase capability row and link the operating guide.
- `docs/midi-input.md` — Describe rate selection, signed offset, generation, chase, Freewheel and control-client commands.
- `docs/roadmap.md` — Record the independent MTC milestone under MIDI devices.

## Measurement reports, images or data (0)

None.

## Other (0)

None.

## Dependency delta

No Cargo.toml or Cargo.lock changes in this layer. Generation uses the existing SoundCraft time/MIDI model and the scheduler from #1662. No measurement scripts, logs, CSV or temporary files remain in the layer. The former native worker spacing probe (observation-only) and its sole atomic-counter import were removed from the MTC worker test module.
