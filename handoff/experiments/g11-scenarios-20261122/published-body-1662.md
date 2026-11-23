<!-- storage-output-timing -->
## Output timing after an audio device reset

A missing or implausible presentation timestamp now has its own state. A stream can retain its last valid measurement; a newly opened device starts with unknown latency, and a genuine measured zero remains valid. Outputs configured for device compensation wait for a usable measurement. Stop and cleanup continue to work. The status distinguishes a driver measurement, a retained one, and an unknown value.

On Windows shared WASAPI, SoundCraft probes the same endpoint ID and stream configuration while stopped. The candidate emits silence and must supply eight consecutive fresh timestamps before it takes over the existing renderer. This preserves instruments, MIDI inputs, routing and the transport position. Playback, recording and pending transport starts prevent the handoff. An unavailable device or an exhausted retry budget leaves the existing manual recovery in Setup → Playback Engine. ASIO keeps its original single-stream callback.

**Verification.** The old code advanced a 15 ms deadline by 15 ms after an invalid report and advertised a new stream's unknown latency as zero. Hardware also exposed a legal final reading of 56.395 ms immediately before invalidation; retaining it alone made the A4 5.699 ms early. Windows playback passed 151 tests, with two environment-dependent tests ignored. Strict playback Clippy passed. Five recovery tests also passed in an ASIO-enabled build. The shared implementation is exercised by [the three Model 12 STORAGE cycles in #1663](https://github.com/storytold/soundcraft/pull/1663).

Once recovery succeeds, the UI clears its obsolete idle-device warning if it is still current. It preserves subsequent messages and the history of an interrupted recording. The UI regression failed before that change and passed after it.

**Open question.** Backends that cannot supply a fresh trustworthy measurement or safely reopen alongside the active stream retain the manual recovery path. Extending automatic recovery to exclusive backends would require a separate backend-specific decision and validation.

On the published head `91366d0`, all seven UI warning and recovery regressions passed on Windows.
<!-- end-storage-output-timing -->

## What this PR does

Setup › MIDI › MIDI Beat Clock sends the session tempo at 24 pulses per quarter note. Enable one or more output ports and enter a signed sample offset for each. A negative offset advances transmission. The effective adjustment is capped at 250 ms at the active sample rate; switching sample rates preserves the saved sample count. Calibration follows the named port across projects on this computer. An older project's calibration is imported once if the port has no saved value. Port names are limited to 1,024 UTF-8 bytes.

This implements the MIDI Beat Clock destinations and offsets described in the Pro Tools Reference Guide 2026.4, pp. 743–744. Preferences › MIDI includes separate external-device delay compensation switches for Beat Clock, MTC, and notes/controllers. Beat Clock compensation defaults on. #1663 connects the MTC switch to its generator. The note/controller option is stored for external track output, which is still pending.

## Shared code

`sync_clock` publishes sample positions and when the audio device expects them to be heard. `sync_output` owns the worker, deadlines, and MIDI connections. The Beat Clock encoder sends Start at zero and aligns off-grid resumes with Song Position Pointer and Continue. Short delays are recovered with spaced clocks; larger discontinuities relaunch the receiver. Multiple encoders can share a single-client output. `setup.midi_sync_status` and **Copy diagnostics** expose per-port calibration, lead, connection status and worker timing.

## Fourth-round changes and verification

The worker can now wait up to two seconds for a local transport change to appear in the rendered timeline. Clock output uses the session map that is actually audible for its destination. Each port schedules its future messages independently; a failed Stop is retried before sending the next stream on a reconnected port.

The port editor retains a saved calibration across sample-rate changes, scrolls long port lists, and shows the applied limit. Negative calibration is bounded by the lead that the device and compensated mixer delay can supply. Playback errors are exposed in the status line and diagnostics. To remove one stored entry use `{"ports":{"name":null}}` in `setup.midi_beat_clock`. To measure calibration, compare several events against the grid and use their mean offset. See the [Pro Tools Reference Guide 2026.4](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf), pp. 176, 743–744, 1476 and 1815.

At `97d8cd0` (including main `5806129`), the playback library passed 142 tests with two ignored in each of one serial and three eight-thread runs. A new contention fixture demonstrates why a single synthetic callback could skip publication while the worker reads the clock. The test now requires the requested pass and playing state to be published before it evaluates the MIDI output. Strict playback Clippy and formatting passed. The [GitHub CI run](https://github.com/storytold/soundcraft/actions/runs/44758045406), Nix and SonarCloud returned `action_required`. On the feature head alone, playback passed 142 (2 ignored), UI passed 352, and engine passed 434 with one failure in `each_movie_is_kept_relinked_or_offline`. The same test passes with the #1536 Windows correction. The local Windows integration `585cc1a` adds #1536 and #1658 to this exact head. Formatting and workspace/all-targets Clippy with warnings denied passed. The three library suites passed 929 tests (engine 435, playback 142, UI 352), with two playback tests ignored.

Follow-up verification on the Beat Clock implementation:
- A transition published 2.5 seconds after Play wakes the idle worker without restarting the polling loop. Before the fix there was no Start. Afterwards the receiver got Start followed by Clock. The timeout counter increased once, and 50 intervening stopped callbacks did not cause worker polls.
- With a 600-frame device callback and 1,024-frame renders, the remaining 424 samples keep their original session and tempo map. The first newly rendered frame changes the active map.
- Switching routes and dropping the output each have a 100 ms regression bound even with a MIDI message scheduled two seconds ahead. The local run measured 7.065 ms and 1.711 ms respectively.
- The recurring UI service retries a rejected route and caches settings only after acceptance. A real late output-port failure reaches the status line alongside an existing audio message. The centered dialog test scrolls through 64 destinations at 1366 × 768 while keeping OK accessible.

The physical off-grid trial also exposed a false timeout when the audio thread had already published the requested transition. Sampling the baseline before the command fixed the reproduced timeout (one before, zero after). A redundant Stop while already stopped also avoids arming the timer.

| Regression | Result on the earlier implementation or an isolated reversal |
| --- | --- |
| Delayed Play, failed worker start | At 180 ms the idle receiver missed Start; reapplying unchanged destinations did not start the worker. The revised test covers 180 ms, 600 ms and a bounded 2.5 s timeout. |
| Calibration, long device lists and deletion | The old dialog changed 24,000 to 12,000 samples, the 64-port dialog pushed OK outside the viewport, and 257 disabled entries exhausted the table. The fixed dialog retains 24,000 until an explicit edit; entering 20,000 at 48 kHz clamps to 12,000. |
| MIDI status and failed Stop | A failed port left only the unrelated audio message in the old UI. Removing an active route lost its Stop error. The tests now check status text, recovery and delivery of Stop before the reconnected stream. |
| Delivery times and session revisions | An excessive advance delivered a pulse at 20,000 µs instead of 21,833 µs. Selecting the newest map unconditionally moved the expected change from 560 ms to 500 ms. Omitting 4,800 samples of compensated mixer delay advanced the clock by 100 ms. |
| Loop boundary and catch-up | The old implementation wrapped at the end of the last rendered block. With catch-up spacing forced to zero, the receiver detects a burst at 1,050,125 µs; the earlier timestamp-only test passed that mutation. |
| Independent ports and message size | A two-second future deadline had no queued wake; the 13-byte test message was dropped. The current tests cover independent delivery, the 16-byte envelope and an explicit error and counter for oversized messages. |

## Open questions

<!-- g11-scenario-audit-20261122 -->
### Unattended performance and studio scenarios

- Should a stopped marker locate transmit SPP immediately? 0/11 stopped locates emitted SPP; all 11 subsequent nonzero starts did.
- Should a recovered output discard expired Clock messages immediately? After 100 ms without a valid timestamp the first F8 was 95.833 ms late on this isolated head (five expired F8s). The 200 ms reset discarded old events and subsequent steady-state handoffs were within 0.833 ms.
- How should independently calibrated, identically named ports be addressed? Two requests (+701/+302 samples) shared one key. Should a timing warning be visible with zero MIDI destinations (20 ms retained, 40 ms unknown, clear at 60 ms)? Is a 0.337 ms difference per 1,000 dense-map locates material? Should a malformed sync preference reset only that field?
- Local long-run command after applying the scenario test overlay: `cargo test -p soundcraft-playback --lib b7_two_hour_pdc_render -- --ignored --nocapture` (two hours of audio per rate, four rates).

[Measurements and local regression names](https://github.com/storytold/soundcraft/pull/1662#issuecomment-7070842940)
<!-- /g11-scenario-audit-20261122 -->


- Q8. Keep the MIDI Notes and Controllers preference visible until external track output is wired.
- Q9. Live plug-in delay changes use the same session-revision timing as other map changes. A separate realignment policy remains open.
- Q14. The existing ±250 ms edit range remains a SoundCraft limit.

## Third-round review and regressions

The output worker now handles a coalesced input notification with a single presentation check. Local transport transitions retain the short polling period needed for the next audio callback. A regression with 50 synthetic notifications reproduced 660 loop iterations before the change. Replacing Beat Clock destinations also preserves previously calibrated ports used by another sender. The prior implementation lost the omitted port’s −201-sample offset. Both probes passed at the third-round head.

## Earlier verification

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

Windows integration on feature head `7b912d8` plus #1536 and #1658 (local merge `9193d63`): `cargo xtask ci` passed. 1,916 workspace tests and doctests passed. This includes strict workspace Clippy and the WebAssembly app build. GitHub Actions: [CI awaits maintainer approval](https://github.com/storytold/soundcraft/actions/runs/44719321422).

## Hardware status

On Windows, SoundCraft sent through the Model 12 USB MIDI port and the UM-ONE recorded the physical DIN output. At `02e63c6`, the Model 12 WASAPI stereo F32 format at 48 kHz supported exactly 480 frames (20 buffer sizes probed). The 20 idle-start trials all delivered Start, Clock and Stop. The first F8 arrived 56.1–81.0 ms after Play. The timeout counter stayed at zero. All eight combinations of 120/180 BPM, origin/off-grid start and 0/−200 samples produced the expected wire sequence. During sustained playback the observed phase shift for −200 samples was −4.521/−4.128 ms at 120/180 BPM (expected −4.167 ms).

At 480 frames, all 20 one-bar loop tests stopped near the end with one Stop and no short restart when Stop was requested 28–60 ms before wrap. A 256-frame test needs another audio configuration. Exploratory requests only 3–6 ms before the nominal boundary crossed an in-flight wrap in four trials. They do not establish a Stop accepted by the audio callback before wrap. The earlier minimized-window test at `02e63c6` delivered Start/F8 and Stop on all five shortcuts, but recorded false timeout increments between runs. At `ed28af4`, all five minimized-window starts passed with zero timeouts; the subsequent `97d8cd0` commit only changes the regression fixture.

On the most recent tested runtime, `ed28af4`, 20/20 idle starts reached the receiver in 57.4–82.8 ms, and five minimized shortcut starts reached it in 491–500 ms. All 25 had zero transition timeouts. The 20 loop-end stops passed again. The eight grid cases passed after confirming the output was connected; one exploratory run started before the port was ready and correctly joined the running transport with SPP and Continue. The sustained −200-sample measurements were −4.268/−4.071 ms at 120/180 BPM.

The R3 wire test at 20 BPM compared a zero offset, a negative offset, then zero again. With compensation on, requesting half the reported lead advanced the receiver by 23.275 ms (expected 23.458 ms). Requesting twice the lead triggered the bound and advanced it by 45.574 ms (expected 45.937 ms). With compensation off, both requests were limited to zero; the receiver shifted by +0.074/+0.337 ms. Maximum difference from expected was 0.364 ms in those four wire measurements.

For the remaining hardware checks, the native R9 dialog has 64 destinations in the 1366 × 768 UI regression. R7/R8 physical USB removal and restoration, and simultaneous audio recordings of the DAW click and the external beat for the R3/R4/P-D5 acoustic thresholds, are still open. The reported USB/DIN offsets measure MIDI arrivals.

The tables above distinguish wire measurements, isolated software tests, and remaining acoustic checks (tracking issue #1661).

## Known limits and deferred work

Calibration is manual. Native OS-timestamped sends, Windows MIDI Services and MIDI Machine Control are deferred. Severe publisher or worker starvation can still interrupt clock delivery.

## Review and merge order

#1536 → **#1662** → #1663 → #1669. #1536 supplies the existing Windows CI fixes. Refresh from main after #1536 lands; refresh the MTC branch after this PR lands. Tracks #1661.


<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

<!-- coderabbit-ai-generated:v1 -->

## Summary by CodeRabbit

- **New Features**
  - Added MIDI Beat Clock output configuration for multiple external devices, with per-device timing offsets and delay compensation.
  - Added playback synchronization status and diagnostic information, plus preferences for Beat Clock, Timecode, and MIDI note compensation.
- **Documentation**
  - Updated MIDI and roadmap documentation to describe Beat Clock output and note remaining hardware verification.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->