## What this PR does

Setup › MIDI › MIDI Beat Clock sends the session tempo at 24 pulses per quarter note. Enable one or more output ports and enter a signed sample offset for each. A negative offset advances transmission. The effective adjustment is capped at 250 ms at the active sample rate; switching sample rates preserves the saved sample count. Calibration follows the named port across projects on this computer. An older project's calibration is imported once if the port has no saved value. Port names are limited to 1,024 UTF-8 bytes.

This implements the MIDI Beat Clock destinations and offsets described in the Pro Tools Reference Guide 2026.4, pp. 743–744. Preferences › MIDI includes separate external-device delay compensation switches for Beat Clock, MTC, and notes/controllers. Beat Clock compensation defaults on. #1663 connects the MTC switch to its generator. The note/controller option is stored for external track output, which is still pending.

## Shared code

`sync_clock` publishes sample positions and when the audio device expects them to be heard. `sync_output` owns the worker, deadlines, and MIDI connections. The Beat Clock encoder sends Start at zero and aligns off-grid resumes with Song Position Pointer and Continue. Short delays are recovered with spaced clocks; larger discontinuities relaunch the receiver. Multiple encoders can share a single-client output. `setup.midi_sync_status` and **Copy diagnostics** expose per-port calibration, lead, connection status and worker timing.

## How it was verified

- `paired_and_periodic_buffers_preserve_grid_without_relocations` exercises 18 combinations of tempo, callback size and delivery pattern. `fractional_limits_never_overshoot_the_next_buffer_and_a_stall_is_capped` checks fractional steps and stopped callbacks. `destination_stamp_includes_device_lead_and_signed_port_offset_once` checks the timing and sign of calibration.
- `one_missed_pulse_advances_without_restarting_external_transport` reproduced the old unwanted receiver restart. The desktop two-port command test also failed before machine settings were implemented. Coverage includes reopening old projects, unavailable ports, rejected long names, and a single-client backend reconnecting after send failure.
- Windows: 123 playback library tests, 345 UI library tests and one model library test passed. Strict playback Clippy with all targets passed. The real-time harness was run separately. The virtual OS port loopback is opt-in and requires a configured port pair. In an isolated mutation run, deliberately breaking the timing, calibration, connection and recovery logic caused 11 named playback regressions to fail; the other 112 still passed.

**Host-side send timing (in-process sink).** Windows, 48 kHz, 180 BPM, precise sleeps, raised worker and simulated publisher priority, no timer-period override. All four runs had one Start and zero Song Position Pointer relaunches.

| Callback / duration | F8 messages | Lateness p95 | Interval error p95 |
|---|---:|---:|---:|
| 64 frames / 5 s | 360 | 1.459 ms | 0.965 ms |
| 256 frames / 5 s | 361 | 1.247 ms | 1.198 ms |
| Paired 1,024 frames / 5 s | 360 | 1.113 ms | 1.035 ms |
| Paired 1,024 frames / 30 s, 10 of 12 logical CPUs busy | 2,160 | 1.012 ms | 1.013 ms |

These measurements end when the sink accepts each message. USB buffering, DIN serialization, and a loaded audio DSP graph still require separate verification.

Windows workspace Clippy passed with all targets and warnings denied on a local integration with #1536. Running the workspace tests on Windows also requires the independent AAF rooted-path correction in #1658: the absolute-locator test fails on the unmodified main + #1536 baseline as well, and all 18 AAF integration tests pass when #1658 is applied. Neither Windows fix is included in this branch.

Final Windows integration gate: `cargo xtask ci` passed for feature head `da2a6ae` plus #1536 and #1658. Cargo reported 1,914 passing tests across all targets and doctests. The gate includes workspace Clippy with warnings denied and the WebAssembly app build.

## Hardware status

Not yet verified on hardware; a hardware check is planned once all three PRs are final (see #1661).

## Known limits and deferred work

Calibration is manual. Native OS-timestamped sends, Windows MIDI Services and MIDI Machine Control are deferred. Severe publisher or worker starvation can still interrupt clock delivery.

## Review and merge order

#1536 → **#1662** → #1663 → #1669. #1536 supplies the existing Windows CI fixes. Refresh this draft from main after #1536 lands; refresh the MTC branch after this PR lands. Tracks #1661.
