# #1669 external Beat Clock follow

Own layer against #1663. 93 paths before packaging and 78 after merging the packaged #1663 head. Production modules with inline tests are counted once under their primary role. Opt-in tests are identified separately.

## Product code

| Path | Purpose | After packaging |
|---|---|---|
| `crates/engine/src/clip_group_file.rs` | Import clip groups through the edit path that preserves followed-take timing. | Retained |
| `crates/engine/src/cmd.rs` | Parse absolute timeline labels separately from zero-based time spans used by edits. | Retained |
| `crates/engine/src/cmd/audiosuite.rs` | Carry followed-take metadata through AudioSuite rendering and clip replacement. | Retained |
| `crates/engine/src/cmd/clip.rs` | Keep clock-take projections synchronized during clip edits, placement and looping; parse a loop length as a duration. | Retained |
| `crates/engine/src/cmd/clip_more.rs` | Route pitch-shift removal through the projection-aware clip editor. | Retained |
| `crates/engine/src/cmd/edit.rs` | Apply cut, clear and clipboard operations to clips and their capture-grid metadata. | Retained |
| `crates/engine/src/cmd/edit_more.rs` | Preserve distinct capture timing through paste-merge, duplicate, spacing, playlist edits and time compression. | Retained |
| `crates/engine/src/cmd/event.rs` | Keep the played and editable note lists consistent when deleting duplicate notes. | Retained |
| `crates/engine/src/cmd/event_more.rs` | Project the copied take on event transforms and parse requested lengths as durations. | Retained |
| `crates/engine/src/cmd/midi.rs` | Remove captured and editable MIDI events together on note deletion. | Retained |
| `crates/engine/src/cmd/more_util.rs` | Replace clips through the projection-aware timeline abstraction. | Retained |
| `crates/engine/src/cmd/options.rs` | Interpret session timecode independently of the existing start and handle persistent automation atomically. | Retained |
| `crates/engine/src/cmd/track.rs` | Copy or promote a playlist range together with its followed-take timing. | Retained |
| `crates/engine/src/cmd/track_more.rs` | Carry original MIDI timing when extracting a track and assigning new clip IDs. | Retained |
| `crates/engine/src/cmd/transport.rs` | Mirror external stopped locates into the edit cursor without issuing a second seek. | Retained |
| `crates/engine/src/edit.rs` | Carry Clock projections through clip splits, trims, paste-merge, moves, and undoable edits. | Retained |
| `crates/engine/src/io.rs` | Expose the Clock-take projection to the engine's recording and editing paths. | Retained |
| `crates/engine/src/io/import.rs` | Place imported material using the projection-aware timeline editor. | Retained |
| `crates/engine/src/io/midi_take.rs` | Capture MIDI against the live grid and store timing that survives editing and project reopen. | Retained |
| `crates/engine/src/io/midi_take/projection.rs` | Map each captured event between played and editable grids, including slicing and recomposition. | Retained |
| `crates/engine/src/io/record.rs` | Place recorded audio and undo the take while preserving prior MIDI projections. | Retained |
| `crates/engine/src/io/render.rs` | Route clip consolidation through the projection-aware editor. | Retained |
| `crates/engine/src/io/strip.rs` | Apply Strip Silence changes to both clip identities and their projection metadata. | Retained |
| `crates/engine/src/lib.rs` | Own playback/recording grids, timeline projections, clipboard provenance and undo state. | Retained |
| `crates/mix/src/click.rs` | Dispatch metronome attacks against the Clock horizon and preserve tails across blocks. | Retained |
| `crates/mix/src/lib.rs` | Provide the mixer with a bounded score interval and an optional device-deadline prediction. | Retained |
| `crates/mix/src/midi.rs` | Schedule clip MIDI events once; preserve ordered overdue attacks and releases when prediction reopens. | Retained |
| `crates/mix/src/midi_clip_bounds.rs` | Project MIDI clip boundaries from their musical positions when the live grid changes. | Retained |
| `crates/mix/src/strip.rs` | Map score offsets into the output block during held and projected ranges. | Retained |
| `crates/playback/src/beat_clock.rs` | Keep the emitted initial F8 from being sent again by the Beat Clock cursor. | Retained |
| `crates/playback/src/callback.rs` | Render Clock-limited or predicted blocks against measured output timing and retire session snapshots safely. | Retained |
| `crates/playback/src/clock_follow.rs` | Decode transport/SPP/F8, estimate tempo/phase, recover from loss, and determine the render horizon. | Retained |
| `crates/playback/src/lib.rs` | Publish tempo-only session snapshots, expose output lead and prepare/cancel external starts. | Retained |
| `crates/playback/src/midi.rs` | Timestamp external MIDI input, publish scheduling bounds and dispatch prepared starts to the player. | Retained |
| `crates/playback/src/mtc.rs` | Emit MTC quarter frames at representable fractional-rate sample boundaries. | Retained |
| `crates/playback/src/mtc_input.rs` | Apply changed MTC reader options and keep full-frame locates aligned at fractional frame rates. | Retained |
| `crates/playback/src/record.rs` | Keep capture overflows in the take that caused them and expose opt-in device-free input. | Retained |
| `crates/playback/src/sync_clock.rs` | Match audible output timestamps and rendered tempo-map revisions as the live grid advances. | Retained |
| `crates/playback/src/sync_input.rs` | Distinguish sustained ramps, abrupt steps and timestamp jitter in observed F8 intervals. | Retained |
| `crates/playback/src/sync_output.rs` | Dispatch generated sync traffic via independent ordered per-port workers. | Retained |
| `crates/playback/src/sync_output/port_io.rs` | Deliver sync messages per destination with bounded queuing and delivery acknowledgements. | Retained |
| `crates/ui-egui/locales/pt-BR/mod.rs` | Translate external Clock setup controls and validation messages into Brazilian Portuguese. | Retained |
| `crates/ui-egui/src/app.rs` | Service external Clock requests and synchronize the playback session during the UI lifecycle. | Retained |
| `crates/ui-egui/src/app/audio.rs` | Protect a prepared external start while opening or reconnecting an audio device. | Retained |
| `crates/ui-egui/src/app/clock_follow.rs` | Handle external transport, update the live beat grid and present follow/record settings. | Retained |
| `crates/ui-egui/src/app/files.rs` | Preserve conflicting external-timecode-offset warnings during session recovery. | Retained |
| `crates/ui-egui/src/app/mtc.rs` | Coordinate online MTC state with external transport, queued record requests and locates. | Retained |
| `crates/ui-egui/src/app/mtc_output.rs` | Manage MTC output routing without erasing independent per-port calibration. | Retained |
| `crates/ui-egui/src/app/playback.rs` | Start the player from the compensated position while preserving the musical origin and avoiding duplicate transport requests. | Retained |
| `crates/ui-egui/src/dialogs.rs` | Expose sync setup and parse counter values against the displayed live beat grid. | Retained |
| `crates/ui-egui/src/dialogs/midi_beat_clock.rs` | Present independent input/output offsets and retain calibrated devices even when disabled. | Retained |
| `crates/ui-egui/src/lib.rs` | Persist external Clock input and loss-policy settings and migrate legacy input-offset sign. | Retained |
| `crates/ui-egui/src/menus.rs` | Route external Clock commands and show the Sync and Follow MIDI Clock menu entries. | Retained |
| `crates/ui-egui/src/midi_sync.rs` | Keep input/output calibration independent and migrate compatible machine preferences. | Retained |
| `crates/ui-egui/src/panels/transport.rs` | Display the playback grid's tempo and musical position in the transport. | Retained |
| `crates/ui-egui/src/preferences.rs` | Expose supported MIDI synchronization preference controls and explain unavailable switches. | Retained |
| `crates/ui-egui/src/toolbar.rs` | Use the active playback map for toolbar position, selection length, meter and tempo. | Retained |

## CI tests and test fixtures

| Path | Purpose | After packaging |
|---|---|---|
| `crates/mix/src/tests.rs` | Regressions for Continue-boundary attacks and same-pitch releases during catch-up. | Retained |
| `crates/playback/src/clock_follow/render_lead.rs` | Render sampler and click PCM against a reference across buffer sizes; guard short-buffer identity, handoff and expiry. | Retained |
| `crates/playback/src/clock_follow/tests.rs` | Exercise wire parsing, jitter, tempo changes, loss policies and relock. | Retained |
| `crates/playback/src/mtc/tests.rs` | Check that the first sample of an even fractional frame emits its full quarter-frame group. | Retained |
| `crates/playback/src/sync_output_tests.rs` | Check pending output and multiport scheduling across external transport and live grid revisions. | Retained |
| `crates/playback/src/tests.rs` | Exercise render handoffs, tempo-map revisions, MIDI clip projection and deferred session retirement. Removed the assertion-free profiling function. | Retained |
| `crates/ui-egui/src/app/clock_follow/tests/coast_relock.rs` | Check distinct PCM attacks and phase on Coast relock and Stop on loss. | Retained |
| `crates/ui-egui/src/app/clock_follow/tests/large_steps.rs` | Check abrupt tempo changes and render-ahead limits using distinct attacks and complete waveforms. | Retained |
| `crates/ui-egui/src/app/clock_follow/tests/packet_steps.rs` | Cover jitter and timestamp coalescing; the separate ten-minute stability regression is ignored by default. | Retained |
| `crates/ui-egui/src/app/clock_follow/tests/ramp_response.rs` | Check gradual source-tempo ramps, slow drift, post-acquisition BPM changes and PCM integrity. | Retained |
| `crates/ui-egui/src/app/clock_follow/tests/recording.rs` | Check simultaneous audio/MIDI recording across loss and resume under both policies. | Retained |
| `crates/ui-egui/src/app/clock_follow/tests/sampler_song.rs` | Create the deterministic sampler/clip fixture shared by PCM regressions. | Retained |
| `crates/ui-egui/src/localization.rs` | Verify localized external-clock validation messages. | Retained |

## User and project documentation

| Path | Purpose | After packaging |
|---|---|---|
| `ROADMAP.md` | Project-level progress entry for external Clock transport and recording. | Retained |
| `docs/gaps.md` | External Clock status and outstanding G-11 gaps. | Retained |
| `docs/hardware-parity.md` | External Clock hardware capability and setup guide link. | Retained |
| `docs/midi-input.md` | User setup, transport, recording, loss policies, calibration and one hardware-qualification sentence. | Retained |
| `docs/roadmap.md` | Detailed roadmap progress entry for incoming MIDI Beat Clock. | Retained |

## Measurement reports, images and data

| Path | Purpose | After packaging |
|---|---|---|
| `docs/external-clock-response-measurements.md` | Per-attack PCM matrices and buffering/ramp findings moved to the evidence comment. | No layer diff |
| `docs/images/midi-clock-256-main-residual.png` | Waveform comparison for the unresolved 256-frame MAIN residual. | No layer diff |
| `docs/images/midi-clock-asio-buffer-sizes.png` | Per-buffer comparison of callback sizes and first F8 to MAIN onset. | No layer diff |
| `docs/images/midi-clock-asio-waveform-detail.png` | Detailed ASIO waveform and short-dropout comparisons. | No layer diff |
| `docs/images/midi-clock-chorus-tempo-step.png` | Chorus tempo-step response. | No layer diff |
| `docs/images/midi-clock-direct-asio.png` | Direct ASIO output versus software monitoring. | No layer diff |
| `docs/images/midi-clock-edm-tempo.png` | Electronic dance tempo-change timing. | No layer diff |
| `docs/images/midi-clock-main-return.png` | Digital playback to MAIN return signal path. | No layer diff |
| `docs/images/midi-clock-resume-boundary.png` | Continue exactly at and immediately after a note boundary. | No layer diff |
| `docs/images/midi-clock-resume-dispatch.png` | Dispatch timing following the first F8. | No layer diff |
| `docs/images/midi-clock-resume-latency.png` | Physical MIDI-to-audio start latency. | No layer diff |
| `docs/images/model-12-main-loop-clock-follow.png` | Physical MAIN loopback versus internal SD and USB returns. | No layer diff |
| `docs/model-12-clock-follow-hardware.md` | Model 12 latency, waveform, routing and recording acceptance report moved to the evidence comment. | No layer diff |

## Other

| Path | Purpose | After packaging |
|---|---|---|
| `ATTRIBUTION.md` | Credits for measured waveform figures. Restored the parent layer's file after removing those figures. | No layer diff |
| `crates/playback/Cargo.toml` | Declare the opt-in test-input feature used by simulated device capture. | Retained |
| `crates/playback/src/sync_timing_test.rs` | Previously adapted the one-off timing probe to asynchronous port delivery. The lower layer removed that probe and moved its separate loopback smoke test; no follow-layer change remains. | No layer diff |
| `crates/ui-egui/Cargo.toml` | Enable the playback crate's test-input feature for desktop recording tests only. | Retained |
| `crates/ui-egui/src/app/clock_follow/tests/slowdown_sweep.rs` | Run the opt-in 96-phase slowdown sweep over both deadline policies; assert complete PCM and exact short-buffer equivalence. | Retained |

## Dependencies

The playback manifest adds the empty `test-input` feature. The UI crate adds the existing workspace `soundcraft-playback` as a dev dependency with that feature so audio/MIDI recording can be exercised without a device. No package version change, new registry dependency, root Cargo.toml change, or Cargo.lock change is introduced in this layer.

The three opt-in external-follow regressions cover eight hours of grid flutter, ten-minute coalesced delivery and a 96-phase device sweep. All have behavioral assertions and are documented in the PR. The removed snapshot profiler only printed host timings. No measurement script, log, CSV or temporary file remains in the committed layer.
