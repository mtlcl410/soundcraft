# MTC transplant and native MIDI output identity audit

Local revision comparison for #1663 at `671b667` and #1669 at `d9a0ec0`. The counts are Rust function definitions in tracked crates and applications.

| Function | #1663 | #1669 | Module |
|---|---:|---:|---|
| `zero_based_param` | 1 | 1 | `crates/engine/src/cmd.rs` |
| `duration_param` | 1 | 1 | `crates/engine/src/cmd.rs` |
| `timecode_labels_for_session_start_and_durations_have_no_session_offset` | 1 | 1 | `crates/engine/src/cmd/options.rs` |
| `full_frame_locate_matches_fractional_rate_session_start` | 1 | 1 | `crates/playback/src/mtc_input.rs` |
| `first_integer_sample_of_an_even_fractional_frame_emits_its_quarter_group` | 1 | 1 | `crates/playback/src/mtc/tests.rs` |
| `offset_edit_repositions_a_stopped_reader_without_another_packet` | 1 | 1 | `crates/ui-egui/src/app/mtc.rs` |
| `online_transition_gates_a_record_command_already_in_the_queue` | 1 | 1 | `crates/ui-egui/src/app/mtc.rs` |
| `online_service_reports_why_a_pending_record_was_refused` | 1 | 1 | `crates/ui-egui/src/app/mtc.rs` |
| `restore_sync_output_ids` | 1 | 1 | `crates/playback/src/lib.rs` |
| `restore_port_ids` | 1 | 1 | `crates/playback/src/sync_output.rs` |
| `bind_configured` | 1 | 1 | `crates/ui-egui/src/midi_sync.rs` |
| `midi_sync_pref_reload_keeps_the_uncalibrated_mtc_only_identity_beyond_256_calibrations` | 1 | 1 | `apps/soundcraft/src/config.rs` |
| `clearing_unused_mtc_calibration_frees_the_shared_port_slot` | 1 | 1 | `crates/ui-egui/src/app/mtc_output.rs` |

The following files have identical Git blobs at both revisions.

- `crates/engine/src/cmd/options.rs` (`fa17f319b33f`)
- `crates/playback/src/mtc.rs` (`49ec5ac7a0fa`)
- `crates/playback/src/mtc/tests.rs` (`0d5a5faea90e`)
- `crates/playback/src/sync_output/ports.rs` (`1b519704597f`)

#1669 restores output bindings into the shared registry and the PortIo worker opens the saved identity. The separate MTC-only selection survives alongside 256 calibrated destinations in both layers.

The #1669 loader did drop the output side of a valid migrated 512-row input/output union after saving and reopening. The unchanged application loader from d9a0ec0 recovered 256 inputs and zero outputs. The correction recovered 256 inputs and 256 outputs, all 257 tested device identities, and no settings reset. The new file-reopen regression also covers a former input subsequently enabled for output. This adds one more identity while leaving the union size unchanged. See `registry-union-red.log`, `registry-union-green.log`, 39f4d34 and 2026ac9.
