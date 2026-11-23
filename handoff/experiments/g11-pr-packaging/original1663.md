<!-- storage-output-timing -->
## Model 12 output timing after USB STORAGE

**Constant offset across takes, original build.** After reopening the output, five Windows digital-loopback takes landed at +10.70 to +11.94 ms (spread 1.24 ms). Without reopening after STORAGE, playback was approximately 40 ms later because an invalid presentation timestamp was taken as zero. The old SoundCraft status bar visibly named the Model 12 and pointed to Setup → Playback Engine → Reconnect audio device. Take 0016 in the original ten-song series had SD audio only.

**Fix.** The shared device timing and Windows shared-output recovery come from #1662. MTC chase uses a measured or retained output latency for phase correction. While the output phase is unknown, the reader still handles locate, timecode, and Stop; it avoids accumulating a spurious hard relocation. The quarter-frame decoder and frame-phase calculation are unchanged. Regression tests reproduced a false relocation with missing timing and confirmed that a driver-reported zero still allows correction. A pending first quarter-frame blocks swapping streams; a stopped locate preserves Online and its 5.000 s cursor.

**Hardware on `62ea084`.** Same process, S‑MU2000 project, 48 kHz Windows shared Model 12 output, physical USB → DIN OUT → Roland UM‑ONE, and the same 781 quarter-frame packets per take. An initial cache-only revision retained 56.395 ms and failed, so the final implementation verifies a fresh stream on the original endpoint. Three independent STORAGE entries and exits restored that endpoint automatically, with no manual reconnect. A4 onsets at the Windows playback tap were **+3.321, +3.183 and +3.181 ms**. The spread was **0.140 ms** and each was within **0.629 ms** of the same process's +3.810 ms pre-STORAGE baseline. The source was freshly reported in each onset window, with no new rejected timestamps.

**Absolute comparison.** All three fell outside the predeclared ±3 ms band around the historical +11.619 ms baseline, on the early side. In the current setup, a newly opened build of the original `ee80920` also measured +2.786 and +3.759 ms. These data support repeatable recovery across STORAGE in this setup. They do not establish a universal output calibration. This replay measured digital playback; the earlier ten SD recordings remain the separate recorder result.

Once recovery succeeds, the UI clears its obsolete idle-device warning if it is still current. It preserves subsequent messages and the history of an interrupted recording. The UI regression failed before that change and passed after it. The published playback crate tree is identical to the hardware-tested 62ea084; only the UI status handling and its tests changed afterward.

On the published head `0819e61`, eight targeted Windows UI regressions passed, including the stopped MTC locate and pending first-quarter-frame guard.
<!-- end-storage-output-timing -->

## What this PR does

Select the reader and generator ports under **Setup › Peripherals › Synchronization**. Use **Online** to chase an external master or **Gen MTC** to enable output. Port selections are workstation settings. Session Setup holds the timecode rate, start label, signed external offset in timecode, and the session Freewheel mode. Synchronization also exposes the selected generator port’s calibration in samples and milliseconds. New sessions start at 01:00:00:00 by default; existing sessions retain their saved start.

The generator sends a full-frame locate on a stopped cursor move and quarter frames during playback. Generation and chase support 23.976, 24, 25, 29.97 non-drop, 29.97 drop-frame and 30 fps. Fractional non-drop rates retain their session cadence using the nearest representable wire rate.

Chase locates on acquisition, runs at the audio sample clock's normal speed, and relocates after sustained drift greater than a frame. A stopped locate protects the first event at that position. Choose None, Frames (4–40, default 8), or Jam Sync. An explicit Stop ends Jam Sync. Take chase offline to record.

Pro Tools Reference Guide 2026.4 references: synchronization peripherals (pp. 184–185, 1820), Session Setup, external timecode offset and Freewheel (pp. 1815–1820), and Gen MTC (p. 1826).

## Shared code

The generator uses #1662's audio presentation timeline, signed per-port calibration, delay-compensation preference and worker. Beat Clock and MTC sent to the same destination share one connection. This branch adds a timestamped MIDI input path and a bounded, windowed pulse estimator used by the external clock follow draft.

## Fourth-round changes and verification

**Group A includes Freewheel (N-7).** Received timecode shows the incoming absolute position even when a session offset is active. Session Setup can capture that position as the proposed Session Start; accepting the dialog applies the change. The chase reader uses the session's existing signed external timecode offset. The reader reports an incompatible incoming rate or sustained speed mismatch. External-device compensation and per-port calibration use the shared scheduler from #1662.

Session Setup offers three mutually exclusive Freewheel choices. None stops on detection of invalid or missing timecode. Frames retains the chosen 4–40 frame limit and defaults to 8. Jam Sync continues on the internal sample clock after lock. An out-of-tolerance returning position must be supported by two consistent groups before Jam Sync relocates. Legacy session and command settings are covered by migration tests. See the [Pro Tools Reference Guide 2026.4](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf), pp. 1816, 1818–1821, 1826 and 1847.

Earlier native Windows verification on `ee80920` (current main and #1662 at `97d8cd0`) passed 176 playback tests and all 372 UI tests. Three playback measurements are opt-in. The engine passed 445 tests and failed its inherited `io::session::open_tests::each_movie_is_kept_relinked_or_offline` Windows directory separator assertion. #1536 corrects that assertion and Windows Clippy. #1658 separately corrects AAF rooted locators. The simulated Windows merge with both prerequisites (`ef7feaf`) passed formatting, strict Clippy for the workspace and all targets, and all three libraries: 446 engine, 176 playback and 372 UI tests passed (994 total, zero failures, three opt-in measurements ignored). Generator output was rechecked on this published head. The reader, session-setting and cable-loss observations below retain their original executable `006a968`. GitHub reports `action_required` for [CI](https://github.com/storytold/soundcraft/actions/runs/44758144637), [Nix](https://github.com/storytold/soundcraft/actions/runs/44758144806) and [SonarCloud](https://github.com/storytold/soundcraft/actions/runs/44758144842) on this head.

- A rejected generator update now leaves both worker and UI settings eligible for retry. Restoring the previous implementation caused `an_mtc_route_is_cached_only_after_the_worker_accepts_it` to retain a calibration even when there was no session or worker to accept it. The corrected version passes, and `recurring_mtc_output_retries_an_unchanged_target_after_the_worker_refuses_it` verifies an unchanged request succeeds on retry and is subsequently deduplicated. This head also preserves the shared scheduler’s late-transport wake and the first rendered sample of a new time-map generation. Local transport now snapshots the presented pass before sending the audio command. The MTC reader captures the external transport baseline while the incoming event is still locked, so the callback cannot consume it first. A repeated external Roll on a playing presentation or Stop on a stopped presentation leaves the worker idle. The regression queues 100 locates, changes the presented pass before the worker consumes its one wake, and checks that the queued snapshot still identifies the original pass.

- The signed offset regression moves an incoming 00:00:10:00 to session sample 480,000 with a one-hour offset at 48 kHz. Restoring the retired setting produced sample 0. The incoming diagnostic stays at the absolute 00:00:10:00 label.
- Rate tests cover incompatible wire codes, all four 24/30 fractional-speed combinations with ±1.2 ms arrival jitter, and ten minutes of matching code on each supported 24/30 variant. Disabling the diagnostic reproduced both missed warnings. The matching-rate control stayed clear. Removing mixer delay reproduced the quarter-frame timing error.
- The Session Setup and Spot tests exercise live capture, keyboard focus, explicit confirmation and rejection of a pre-start clip edge. Returning an unused generator port calibration to zero frees its stored slot. The GitHub [CI](https://github.com/storytold/soundcraft/actions/runs/44749407619), [Nix](https://github.com/storytold/soundcraft/actions/runs/44749407882) and [SonarCloud](https://github.com/storytold/soundcraft/actions/runs/44749408056) workflow runs for the earlier hardware-test revision `006a968` reported `action_required`.

- **None.** Missing timecode for a full group or a discontinuous quarter frame stops the transport without coasting. Short jitter stays locked. The test failed when the loss correction was reversed.
- **Frames.** The 4-, 8- and 40-frame tests cover the last instant before expiry and the first instant at expiry, the reported elapsed and configured frame counts, recovery inside tolerance, and stopping after sustained loss.
- **Jam Sync.** A reader that has never locked stays idle. A locked transport advances its sample position for ten seconds without incoming code. An in-tolerance return keeps the same roll. A one-second jump requires two consistent groups. Before the callback fix the second group produced **zero** relocations; the regression requires **one**. An explicit Stop still ends playback.
- **Session compatibility.** Legacy Jam and frame-count settings migrate on load, switching session selects the saved policy, and the legacy command fields continue to work. Changing modes preserves the stored frame count. Tests cover mutual exclusion, the 4–40 range, and the default of eight.
- **Clock mapping and stale UI events.** The old driver-time mapping measured 3,000 µs error after a five-second pause. Bypassing the mapping failed the 500 µs drift bound at 1,200 µs. Restoring stale Stop handling restarted the callback at sample 7,440 instead of advancing to 7,680.
- **Group A and related UI.** Tests cover incoming absolute timecode, captured Session Start before and after acceptance, shared signed offset, rate-mismatch warnings, sample-rate changes, MTC output compensation, pre-start Spot, unsupported rates, and Online keyboard control. Isolated reversals yielded 3 failing engine, 4 failing playback and 6 failing UI probes. The Online recording restriction remains; #1661 tracks Record Online separately.

## A-10 verification after output timing loss

At 25 fps, after timing was unknown from 100 to 200 ms, the old first QF was 100 ms late. The fix sends one full-frame locate at 200 ms for 00:00:00:05, skips the obsolete pieces, and starts the next complete QF group at 240 ms. Piece 0 reached the simulated port at its deadline (+0 ms), followed by pieces 1–7 every 10 ms. The 40 ms wait is the time to the next group boundary. A separate 20–50 ms gap verifies a live locate even close to the transport origin.

Local Windows playback suite: 191 passed. Workspace rustfmt and playback Clippy (all targets, warnings denied) passed. Merge order: #1662 → #1663 → #1669.

## Open questions

<!-- g11-scenario-audit-20261122 -->
### Unattended performance and studio scenarios


- Should full-frame chase use Session Setup’s rounding at fractional boundaries (67,793 cases one sample early here, 0 in the identical #1669 run), and should raw-payload real-time bytes be stripped before decoding (0/6 decoded)? A queued Online Record gave no visible reason, though all three record paths wrote zero files.
- Should timecode continue into another day at midnight? Should Keep Clips at Their Timecode move automation when Automation Follows Edit is enabled? The 13 clips moved while automation, marker and tempo did not. Should malformed sync fields be recoverable per field?
- Local test overlay commands: `cargo test -p soundcraft-playback --lib scenario_c4_two_hour_drift_render -- --ignored --nocapture --test-threads=1` and `cargo test -p soundcraft-ui-egui --lib scenario_c7_chase_under_150_track_load -- --ignored --nocapture --test-threads=1`. At ±50 ppm the documented relocates produced up to 33.414 ms audible deviation.

[Measurements and local regression names](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7070844245)
<!-- /g11-scenario-audit-20261122 -->


- Q1–Q3. Received timecode is displayed in Session Setup. The existing before-start message stays in place. The incoming rate is available in diagnostics and mismatch warnings.
- Q4–Q5. The offset editor accepts a signed offset directly. MMC offset policy is separate.
- Q6–Q7. When two nonzero legacy offsets disagree, retain both and use the session's canonical offset with a load warning. Preserve the sample duration across rate changes and use the existing timecode formatter.
- Q11. Keeping absolute clip positions moves clips only. Retain existing undo behavior, and reject a move that would place a clip before session start.
- Q12–Q13. Keep the existing warning colors and Gen MTC button visibility.
- Q15. Local transport keeps its current behavior while Online.
- Q17. Recording while Online remains a separate proposal. Relocation during recording and how loss ends a take are deferred to that proposal.

## Third-round review and regressions

- The Freewheel policy and frame count follow the saved session across close/open. Existing sessions without these keys use the defaults. Rate-only changes preserve the start label at all six supported rates. Closing a session opens a fresh one-hour project.
- The selected MTC output port now shows calibration in samples and milliseconds. The desktop command and the Beat Clock dialog share the value. At 48 kHz, +240 samples appeared as +5,000 µs in worker diagnostics with compensation off.
- Scripts and counter entries reject absolute labels before Session Start and preserve the existing selection. External full-frame and quarter-frame input leaves the cursor in place and reports “Before session start”; returning to range restores chase. Relative minutes/seconds and legacy zero-start documents retain their behavior. An actual headless UI interaction enters the invalid label and checks the displayed explanation.
- A one-hour synthetic timestamp test reproduced 360 ms of error at −100 ppm. A rolling minimum reduced maximum error to 0.30 ms at −100 ppm and 0.20 ms at +100 ppm. Diagnostics now report the p95 input arrival delay. A callback/host ordering test also reproduced continued playback after going offline; ending chase now works before the UI observes Roll. Steady quarter frames update the reader without waking the worker for every group.

## Earlier verification

- The pre-fix playback suite failed the fractional generator and native lock-without-repaint probes. The old new-session command returned a zero-hour start. The corrected suites exercise the resulting behavior.
- `all_six_rates_align_eight_wire_pieces_and_session_offset_to_presentation` checks wire labels, cadence and sample positioning. `stopped_locates_drop_frame_labels_and_delayed_worker_resumes_a_whole_group` covers drop-frame minute/tenth-minute boundaries and stale quarter frames.
- `locked_device_tracks_and_stops_during_a_ui_stall` and `external_lock_starts_and_runs_at_unity_without_repaints` cover callback-side acquisition, grace, forced drift, and loss. The virtual run retained the 5.000 s anchor, measured 499.979 ms between the first two onsets, and had zero samples of phase error at the simulated 17 s checkpoint. In the sustained-drift case the transport sought once after the qualification interval. These are simulated sample-clock results.
- The existing selection-range integration test caught an ambiguity with the new one-hour session start: the main timecode counter could interpret the end of an elapsed range as an absolute label. The regression now covers both 0:12.500–0:20.000 and selections entered with full timecode labels from the one-hour origin. The test passed after disambiguating fractional minutes/seconds input.
- A virtual generator-to-slave loopback compared 301 audible positions with 30 ms output lead at each device and a 1 ms phase-error bound. The desktop diagnostics test failed when its reader counter was missing and passed after wiring it to the MIDI input feed.
- Windows playback suite: 139 passed; three timing or OS loopback tests are opt-in. The native playback crate passed strict all-target Clippy and the WebAssembly playback crate compiled successfully. The MTC benchmark used the actual worker, Rust precise sleeps and an in-process sink. At 24 fps (480 messages) p95 interval error was 0.417 ms and p95 handoff lateness 0.561 ms. At 30 fps (600 messages) these were 0.343 and 0.547 ms. Neither run had an interval below 1 ms. This measures host handoff only.

Windows Clippy passed for playback, engine and UI with all targets and warnings denied on a local integration with #1536. Running the workspace tests on Windows also requires the independent AAF rooted-path correction in #1658: the absolute-locator test fails on the unmodified main + #1536 baseline as well, and all 18 AAF integration tests pass when #1658 is applied. The integrated engine, playback and desktop UI library suites passed 426, 139 and 353 tests respectively. Neither Windows fix is included in this branch.

Windows integration on feature head `c147f92` plus #1536 and #1658 (local merge `f1df5ae`): `cargo xtask ci` passed. 1,956 workspace tests and doctests passed. This includes strict workspace Clippy and the WebAssembly app build. GitHub Actions: [CI awaits maintainer approval](https://github.com/storytold/soundcraft/actions/runs/44720085370).

After a prerequisite is squash-merged, compare its landed tree with the reviewed prerequisite head before refreshing this branch. Preserve the incremental changes here and reconcile any newer main changes explicitly.

## Hardware status

The cable-loss tests below were performed on the physical recorder. The regression suite above used a simulated source.

### Generated MTC on the Model 12 and UM-ONE

**Earlier hardware build `ee80920`.** On the Model 12 USB → DIN OUT → Roland UM-ONE loop, the six configured rates again produced the expected wire code and in-order quarter frames (245, 246, 255, 305, 306, 306 in the six 2.6-second windows). The driver’s shortest intervals were 7, 8, 7, 5, 5 and 5 ms respectively. Stopped seeks produced 00:00:59;29 → 00:01:00;02 and 00:09:59;29 → 00:10:00;00. On the shared port a +240-sample request at 48 kHz shifted MTC by +5.071 ms and Beat Clock by +4.910 ms. The generator run passed 52 checks. An independent preallocated native WinMM receiver on the same binary passed all 23 further checks: five minimized 30 fps rolls produced 1,890 successive pieces with zero gaps in the sequence, shortest driver intervals of 5–6 ms, and zero reported stale messages or transport timeouts. Exact fractional progression is covered by the deterministic tests; the short wire captures exercise end-to-end delivery.

**Earlier revision `006a968`.** SoundCraft sent to the Model 12 USB MIDI port and a Roland UM-ONE captured its DIN output. The recorder’s own sync output was off. With the window restored, all six configured frame rates produced complete quarter-frame sequences, the expected rate codes and cadence. Minimum WinMM intervals were 7, 7, 6, 5, 5 and 5 ms respectively (23.976, 24, 25, 29.97 ND, 29.97 DF, 30). These 2.6 s captures establish delivery and cadence. The 23.976/24 and 29.97 ND/30 pairs share wire codes; deterministic long-run vectors establish their exact fractional progression.

- A new session emitted 01:00:00:00. Stopped full-frame messages decoded as 00:00:59;29 → 00:01:00;02 and 00:09:59;29 → 00:10:00;00 at the first sample within each target frame.
- MTC and 120 BPM Beat Clock both came back from one selected port with complete sequences in the stable windows. Changing the common calibration by +240 samples at 48 kHz (+5 ms) shifted MTC by +5.23 ms and clock by +4.95 ms relative to the repeated zero-offset baseline. The single-open invariant is tested separately with an instrumented connection.
- The MIDI Beat Clock and Synchronization dialogs both displayed the saved 20,000 samples on opening at 48 kHz and indicated the 12,000-sample effective limit. Across 96 → 48 → 96 kHz the requested value remained 20,000 and diagnostics reported effective values 20,000 → 12,000 → 20,000.
- Ten pairs of synthetic UI Space presses and ten pairs of targeted Win32 key messages each started and stopped output. From request to the first received quarter-frame the observed ranges were 67.2–87.2 ms and 54.9–64.3 ms respectively.
- With Windows reporting the test window minimized, five rates returned complete groups. The initial Python capture at 30 fps had one missing quarter at a 1.008 s host callback stall. Its WinMM gap measurements did not show a sub-millisecond burst. A separate native WinMM recorder preallocated its callback buffer and wrote the trace only after disconnect. Five minimized 30 fps repetitions captured 1,891 consecutive quarter frames (378, 378, 378, 378, 379). There were no missing pieces, the minimum per-run driver intervals were 4–5 ms, and all 23 checks passed. The single earlier observation remains unattributed.

### Reader rate and signed offset on the Model 12

The Model 12 sent 30 fps non-drop to `006a968`. With the session at 29.97 non-drop for 180 seconds, the first warning appeared at 10.121 s. The median speed deviation was +1,000 ppm, with five hard relocates and zero losses. With the session at 25 fps over 30 seconds, the first poll at 7 ms already showed the incompatible rate, and the warning was present in all 116 samples. With a matching 30 fps session over five minutes, all 1,338 snapshots showed lock, with zero rate warnings, relocates or losses.

With Session Start at 01:00:00:00 and zero offset, RPC reported “Before session start” and the transport stayed stopped. Applying a +01:00:00:00 offset allowed lock, while the incoming diagnostic continued reporting the recorder’s absolute labels from 00:00:04:26 through 00:00:11:22. Restoring zero offset returned to “Before session start”. These readings validate the command and reader path. Physical GUI capture and a synchronized comparison of the two displayed counters are pending.

### Model 12 cable-loss checks for Group A

Tested at `006a968`, 48 kHz, 30 fps non-drop, using the TASCAM Model 12 recorder’s MIDI OUT (DIN) into the Roland UM-ONE. The recorder kept rolling through each cable interruption. Timing below is from SoundCraft RPC observations.

- [x] **None.** SoundCraft stopped with last received timecode 00:00:14:02. The freewheel entry counter did not increase. The reader reacquired lock at 00:00:18:22.
- [x] **Frames, 8.** Last received timecode before interruption was 00:00:07:22. From the first observed 0/8 coasting status to the observed stop was 248 ms. At 7/8 the transport was still playing. After reconnection the reader briefly lost lock again and settled at 00:00:14:18. The cause of the brief loss remains undetermined.
- [x] **Jam Sync.** Last received timecode before interruption was 00:00:12:02. The transport kept playing until the reader returned to locked 14.567 s later. The lock/loss counters stayed at 6/5. Stopping the recorder left SoundCraft running on its internal clock. Taking SoundCraft offline stopped transport.

Not yet verified on hardware; a hardware check is planned once all three PRs are final (see #1661).

### Model 12 recording to SD while sending MTC

- [ ] **H-MTC-SD tested; onset repeatability criterion unmet.** The Model 12 recorded to SD while sending MTC. See the three measured takes below.

Use 48 kHz and 30 fps non-drop. Connect Model 12 MIDI OUT (DIN) → UM-ONE → SoundCraft MTC Reader. Record the firmware version, actual Model 12 menu settings and armed channels. Enable MIDI TIMECODE. Set SoundCraft Online, Gen MTC off and Freewheel to Frames (8). Use a backing project with a known, distinct attack inside every take. Log the session start and external offset so the expected attack can be placed on the SD song timeline.

1. Start SD recording with the live input and backing return armed. First confirm that advancing MTC reaches the UM-ONE/WinMM capture while the recorder is rolling. If there is no MTC, check the same cable, port and capture with ordinary playback. If playback sends code and recording reproducibly does not, stop and document the Model 12 result, firmware and settings.
2. Capture three SD takes of at least 60 seconds each. Include a start at a nonzero position. During one take, disconnect only the DIN cable for about one second, then reconnect it while SD recording continues.
3. For each take, retain the SD tracks, time-stamped MTC and SoundCraft transport log. Verify lock, playback and stop, SoundCraft recording inactive throughout, and no application error. Measure the backing attack relative to its expected song position in milliseconds, accounting for each take’s start. Report the three signed offsets and their spread (maximum minus minimum).
4. For the cable-pull take, report elapsed Frames freewheel, stop and reacquisition, and whether a relocation jump is audible in the SD take. The eight-frame allowance at 30 fps is about 267 ms. Recording into SoundCraft while MTC Online remains a separate follow-up under #1661.

<!-- H-MTC-SD-results -->
**Model 12 SD recording with MTC chase (November 21, build `ee80920`).** On firmware 1.30 0088, the Model 12 recorded CH1 (live mic) and CH2 (S‑MU2000 piano returned over USB) to a 48 kHz / 24-bit SD song. MIDI TIMECODE was on and MIDI CLOCK/SPP was off. The rear DIN output fed the SoundCraft reader via UM‑ONE at 30 fps non-drop, with zero session start and offset, Online enabled, Gen MTC off and Freewheel set to eight frames. All three takes locked, played the backing and followed stop. No transport poll showed SoundCraft recording, an RPC error or a frame-rate mismatch.

| SD take | Start | Recorded | DIN quarter frames | CH2 onset of the scheduled 5.000 s A4 |
|---|---|---:|---:|---:|
| 040208_0004 | Song start | 69.552 s | 8,344 | 5.0135 s (+13.5 ms) |
| 040208_0007 | 2.000 s | 65.680 s | 7,880 | 5.0515 s (+51.5 ms) |
| 040208_0009 | Song start, DIN interrupted during recording | 65.640 s | 7,662 | 5.0555 s (+55.5 ms) |

The onset offset varied by **42.0 ms** across takes using 1 ms RMS windows. Matching the same piano attack independently gave a 41.75 ms spread. The end-to-end measurement does not isolate the source. Both SD tracks were populated in all three takes. The third take’s microphone peaked at −89.08 dBFS, too quiet to verify speech.

During the 1.758 s DIN interruption, the reader reached 8/8 frames and stopped. The first locked-and-playing poll was 311 ms after timecode returned. The SD backing contains the note at 11 s, silence at the expected 12 s attack and the note at 13 s. On replay against the uninterrupted take, the listener heard the pause and no additional click, repeated note or skip on recovery.
**Timing investigation (ten additional SD takes).** Five takes started at the song head and five at 2 s. Relative to the scheduled 5.000 s A4, SD onset ranged from +13.896 to +56.771 ms (median +52.323 ms, spread 42.875 ms). Nine takes also had time-stamped WASAPI render and USB input captures aligned to the UM-ONE DIN trace. The render-tap spread was already 43.590 ms. Two independent microphone marks per take placed the SD timeline on the USB input clock with only 0.353 ms of between-take variation in its origin against DIN. Take 0016 had SD audio only after an endpoint invalidation interrupted the external capture. The original 42 ms spread is not evidence of frame quantization or an MTC accuracy ceiling.

A controlled replay sent the same captured quarter-frame sequence back through the physical DIN link. With the invalidated Windows audio stream, SoundCraft rejected the presentation timestamps and used zero lead. The three measured A4 delays at the Windows render tap were 50.861, 50.298 and 48.713 ms. Reopening the same 48 kHz Model 12 output in the same SoundCraft process restored 35.708–42.708 ms of reported lead. Five valid A4 delays ranged from 10.704 to 11.943 ms (median 11.619 ms), a **38.679 ms median improvement**. One additional capture after the reopen had a WASAPI discontinuity in the onset search window and was excluded. This replay measured the Windows render tap; the ten SD takes are the independent recorder measurement.

**Original reproduction (`ee80920`).** Entering and leaving USB STORAGE invalidated the Windows shared-audio stream. The status bar displayed the unavailable Model 12 output and the Playback Engine reconnect instruction. The original recovery used a manual reopen. The automatic-recovery results and the tested revision are above. Take 0016 retained its SD audio only.
<!-- end-H-MTC-SD-results -->

## Known limits and deferred work

Sustained differences between device clock speeds produce occasional position jumps. Continuous speed control and resampling, online recording under MTC, MMC, guided loopback calibration, native timestamped send APIs and Windows MIDI Services remain separate work.

## Review and merge order

#1536 → #1662 → **#1663** → #1669. This draft includes the prerequisite commits because the upstream repository has no matching fork branches to target. Review the [increment over #1662](https://github.com/mtlcl410/soundcraft/compare/feat/g11-midi-beat-clock-out...feat/g11-mtc-generate-chase). Refresh from main after #1662 lands, then refresh the clock-follow draft. Tracks #1661.
