## What this PR does

**Setup › MIDI › Sync** opens the external clock section of **Setup › Peripherals › Synchronization**. SoundCraft can follow a sequencer, an MPC or a third-party Link-to-MIDI-clock bridge. SoundCraft follows the incoming 24 PPQN tempo and transport. This extends the MIDI Beat Clock workflow in the Pro Tools Reference Guide 2026.4, pp. 743–744, which documents sending clock.

Start selects song zero and rolls on the next clock. Continue resumes, a stopped Song Position Pointer selects a six-clock (sixteenth-note) position, and Stop ends playback. The transport estimates tempo on a transient beat grid and preserves the saved session tempo map. Audio and MIDI recording are available during Beat Clock follow. Each input has a workstation calibration in samples. A negative value advances the follower. Input and output calibration are stored separately, including when both directions have the same port name. An older positive input advance migrates once to the corresponding negative value.

On clock loss, the default is to coast at the last tempo. Stop-on-loss is also available. A new Start/Continue rearms the follower. Setup rejects simultaneous MTC chase and Beat Clock follow and prevents sending clock to the followed port. The diagnostic command reports state, BPM, jitter, phase error and dropout count.

## Shared code

This depends on #1663's timestamp mapping and windowed pulse estimator and #1662's presentation clock and sync status. The input path coalesces clock pulses and bounds queued transport transitions. Tempo changes affect the playback grid without resampling the audio. The user guide includes routing an external sequencer and an independently installed Link bridge.

## Regression and performance evidence

- `continue_after_a_backward_spp_ignores_the_previous_pass_grid` sends a backward Song Position Pointer, changes the external tempo and resumes with Continue. Reusing the previous pass's future tempo changes produced 2,461 samples of error (51.27 ms at 48 kHz). Rebuilding the transient grid at the locate reduced peak error to 0 samples in this sequence.
- `a_follow_grid_revision_changes_pulse_spacing_at_its_audible_block_without_relocating` uses a simulated output with 50 ms of device lead. Treating a live tempo correction as a document edit sent a spurious Stop, SPP and Continue at 560 ms. The fix preserves the original Start and changes pulse spacing when the matching audio block becomes audible. `a_slow_sync_route_can_publish_more_than_eight_live_grid_revisions` previously exhausted the two-slot snapshot pool. The 24-update probe now exercises bounded reuse with eight retained worker maps.
- `negative_input_offset_moves_the_follow_transport_earlier` reproduced a −480-sample calibration moving the cursor to 23,520 against a reference of 24,000. It now yields 24,480. The same-named-port test keeps −480 input and −200 output independent, including output removal and MTC generator deselection. Migration tests cover legacy +480 → −480 and preserving a saved 24,000-sample calibration after a sample-rate reduction while rejecting a newly entered out-of-range value. The original settings omitted directional calibration keys, kept the legacy sign, and rejected an unchanged calibration.
- `sync_menu_and_peripherals_share_the_external_clock_controls` exercises the actual Synchronization dialog and its Follow and Stop-on-loss controls. The previous Sync menu opened a separate window. The change follows the placement of synchronization ports on pp. 184–185 of the Pro Tools Reference Guide 2026.4. Pages 743–744 document Beat Clock output and p. 1819 documents timecode/sample offsets. SoundCraft applies the negative-advance convention to its own Beat Clock input extension.
- In the two-hour synthetic 120 → 150 → 120 BPM ramp, 388,800 clocks produced 531 tempo events and a peak phase error of 164 samples (3.42 ms at 48 kHz). The opt-in eight-hour profile used 1,382,400 clocks at 120 ±0.2 BPM, recorded 3,841 tempo events and a peak error of 149 samples. Across 230,400 indexed tick-to-sample lookups, p99 was 100 ns and the observed maximum was 35.8 µs on this host. These durations cover the lookup itself. Previous synthetic checks also cover Start + 200 clocks reducing notifications from 201 to two, the 960-tick recorded quarter, reconnect/loss policy, USB-like batching and noise without a transport start.

- The host receives four Beat Clock transport notifications in the burst test. Incoming Clock events have no audio command pending, so they schedule zero output-worker transitions. The previous expectation of four premature worker wakes failed. The desktop test `follows_only_the_selected_port_retains_project_tempo_and_allows_record` applies the accepted PlayFrom, Locate and Stop requests. `player_wakes_a_parked_clock_output_for_follow_transport` uses a real Player, silent audio callback, parked output thread and simulated MIDI sink. The applied commands emitted Start, Clock and Stop with zero transition timeouts.

## Windows verification

On the earlier PR revision `2aa39ff`, formatting passed, the playback library passed 188 tests (4 opt-in tests skipped) and the UI library passed 383 (1 opt-in performance profile skipped). The engine library passed 446 tests with the existing Windows movie-relink failure covered by #1536.

An earlier Windows integration at `e8d19ca` (feature `1016a7e` plus #1536 and #1658) passed all seven `cargo xtask ci` gates, with 2,025 tests passed and five ignored across Cargo summaries. Revision `2aa39ff` merged main `5806129`, #1662 `97d8cd0` and #1663 `ee80920`. The final integration at `0a8f553` passed all seven gates: formatting, strict workspace/all-targets Clippy, workspace tests, doctests, assets, dependency layers and WebAssembly. Across 58 Cargo summaries, 2,040 tests passed and 5 were ignored.

GitHub reports [CI](https://github.com/storytold/soundcraft/actions/runs/44759630486), [Nix](https://github.com/storytold/soundcraft/actions/runs/44759630267) and [SonarCloud](https://github.com/storytold/soundcraft/actions/runs/44759630429) as `action_required` for `2aa39ff`.

## Hardware verification

The TASCAM Model 12 recorder drove SoundCraft `104a9fc` over DIN via the Roland UM-ONE with input calibration at zero. Independent captures on Model 12 USB MIDI and UM-ONE DIN each recorded 842 clocks, one Start, one Continue and two Stops. SPP values during the two passes were 0, 88, 41 and 93 sixteenths. A later SPP=0 brings the full capture to five SPP messages on each path. After the backward 88 → 41 locate, the recorder sent Continue and SoundCraft resumed and stopped. The median measured wire tempo was 120.00 BPM on both passes, and SoundCraft's locked medians were 120.008 and 120.009 BPM.

The recorder operated at the same tempo on both passes. A separate PC-generated test drove 120 → 100 BPM through Model 12 USB → Model 12 DIN OUT → UM-ONE. Both loss policies passed eight wire/host checks each. Each run observed 315 clocks, two SPP messages, Start, Continue and two Stops. During a 1.1 s clock interruption, SoundCraft continued with **Coast** and stopped with **Stop on loss**. The backward SPP=12 located sample 72,000 at 48 kHz. Incoming 100 BPM clocks while stopped preserved that position until Continue. Host BPM medians were 120.015 → 100.000 and 120.005 → 100.002 respectively. Measuring click-to-click phase after input calibration requires simultaneous audio references. See #1661.

The same physical-loop script was repeated after the final merge using Windows integration binary `0a8f553` (#1669 `2aa39ff` plus #1536 and #1658; SHA-256 `f02d245af33e29ca3389f2e6cb9dfb1f293fb1e7745cd14ac4e69b41def88f83`). The synchronization, playback and UI sources match the PR. The DIN tap measured 120.00 → 100.00 BPM for both policies. Locked host medians were 120.006 → 100.004 for Coast and 119.996 → 99.998 for Stop on loss. Both passed all eight checks, counted 315 clocks and located to sample 72,000. No operator action was required for this scripted tempo change.

## External MIDI Clock resume at a note onset

Fixes #1674. When output-latency compensation moved the first render buffer ahead of the Song Position Pointer, the hosted-instrument scheduler also skipped the requested note onset. The transport now supplies both the musical origin and the compensated render cursor. A boundary note is dispatched in the first eligible buffer and receives its release even when shorter than the startup latency. An onset before the external position is excluded. The shared playback path uses the project's tempo and sample rate and needs no device mapping.

The regression failed on the previous revision (zero attacks at the boundary). It now exercises two tempos and locate points, short and sustained notes at the boundary, an earlier still-sustaining note, positive and negative compensation, and an empty buffer before the first sounding block.

**Physical MIDI loop and audio capture.** The same eight-bar S-MU2000 accompaniment was played using exact computer-generated Song Position Pointer and Continue messages routed through the Model 12 USB MIDI → hardware DIN OUT → UM-ONE → SoundCraft. Each external run captured all 144 Clock messages. The audio was recorded both at the 48 kHz digital output and at the Model 12 MAIN mix after routing playback to ASIO channels 9/10 at 44.1 kHz.

| Start position at 120 BPM | Repetitions | Crash at digital output / MAIN mix |
|---|---:|---|
| SPP 64, 8.000 s (on the crash) | 2 | Once on each path, in both takes. It was the first audible attack. |
| SPP 65, 8.125 s (after the crash) | 2 | Zero on both paths. The later accompaniment matched the reference waveform in both takes (correlation > 0.997). |
| SPP 60, 7.500 s (one beat of lead-in) | 1 | Once on both paths. |

The from-head reference produced one crash on each path. Counts include the recorded tail after Stop. The earlier Windows integration missed the exact-position crash on this same loop. For the two exact-position runs, the measured first Clock to digital capture delay was 40.25 / 46.82 ms; to the MAIN mix capture, including the monitoring bridge, it was 117.34 / 123.63 ms. These are end-to-end measurements for this route. The onset was present at the first audible sample in each take; acoustic speaker latency was not measured. Hardware verification used the Windows integration base `0a8f553` plus the identical fix (stable patch ID `947f5aa1a68b`).

**Verification on `baab55e`.** Formatting passed. The mix, playback and UI libraries passed 100, 188 and 383 tests respectively; five opt-in tests were ignored. The unintegrated Windows engine library passed 446 tests with its known movie-relink failure tracked by #1536. With the Windows prerequisites integrated, the same four libraries passed all 1,118 executed tests, including movie relink and the new resume regression (five ignored). Strict all-targets Clippy for those four crates completed successfully on that integration. GitHub marked [CI](https://github.com/storytold/soundcraft/actions/runs/44777497735), [Nix](https://github.com/storytold/soundcraft/actions/runs/44777497588) and [SonarCloud](https://github.com/storytold/soundcraft/actions/runs/44777497561) as `action_required` for this revision.

## External Clock resume latency

Fixes #1675. Continue used to clone and publish the current project again, including preparing its instruments, before submitting Play. The player now reuses its prepared snapshot only when both the source document and the published tempo grid still match. Edits, a new player, or an unpublished tempo change take the full preparation path. The scheduling change for #1674 stays in place.

Four exact-position resumes per build used the same project and 120 BPM physical MIDI loop. Temporary probes timestamped MIDI reception, host dispatch, session preparation, audio callback receipt and completion of the first mixed block. They are excluded from the PR. Times below are milliseconds.

| First Clock to downbeat, by stage | Before | Fixed |
|---|---:|---:|
| Input to host processing | 14.5–15.0 | 14.7–31.2 |
| Session preparation | 7.404–7.565 | 0.001–0.002 |
| Command to callback | 2.9–9.6 | 1.0–7.4 |
| Callback to first mixed block | 2.1–2.8 | 2.1–2.8 |
| Input to completed first mix | 27.6–34.9 | 18.5–34.6 |
| First mix to digital loopback | 12.4–13.0 | 11.8–14.6 |
| First Clock to digital crash, mean (range) | 43.8 (40.3–47.9) | 37.9 (31.9–47.2) |

The longest fixed take spent 31.2 ms waiting for host processing. The reduction in repeated preparation does not guarantee a fixed end-to-end response time.

**Monitoring path.** Separate waveform taps sampled digital loopback, bridge input, ASIO 9/10 output callback and the Model 12 USB MAIN mix return. After warming the streams, the uninstrumented Windows integration ran 20/40/60 ms test-queue prefills twice in reverse order on the return pass. Digital-loopback-to-MAIN measured 45.1 / 41.1 ms, 59.3 / 60.3 ms and 82.3 / 74.5 ms respectively. At 60 ms prefill the bridge capture to ASIO callback contributed 68.9 / 62.0 ms and callback to MAIN contributed 15.4 / 14.5 ms. The independent digital taps have a small timestamp offset. This accounts for a delay of the size of the earlier ~77 ms observation; the original two recordings lack the intermediate timestamps to identify their exact split. These figures measure the USB mix return, not acoustic speaker latency. One exploratory 20 ms prefill before the warm-up control produced an outlying 145.9 ms bridge-path total (121.7 ms observed software FIFO wait).

The uninstrumented build produced one crash on both digital and MAIN in all six 8.000 s takes, zero in both 8.125 s takes. Later accompaniment was present. On the original PR branch, the mixer, playback and UI libraries passed 672 tests (five ignored). The new regression failed first on the redundant rebuild, then passed; it also checks document edits, tempo-only updates and ordinary playback replacing a snapshot. Formatting and Windows integration strict all-targets Clippy on the changed crates passed.

![External MIDI Clock resume latency](https://raw.githubusercontent.com/mtlcl410/soundcraft/f5de549f4676119e3299899da7421ec01c809f6d/docs/images/midi-clock-resume-latency.png)

![Crash onset and waveform correlation](https://raw.githubusercontent.com/mtlcl410/soundcraft/f5de549f4676119e3299899da7421ec01c809f6d/docs/images/midi-clock-resume-boundary.png)

## Dispatch after a stopped MIDI Song Position locate

The previously observed 31.188 ms spanned receipt of the first Clock to entry into the host Play handler. That take did not record OS scheduling or individual frame stages. On the previous head (`f5de549`), eight new takes placed host-logic entry at 14.391–15.349 ms after input. The wakeup call had returned by 0.001–0.514 ms, and the remaining in-frame work to the Play handler took 0.012–0.043 ms. The 31.188 ms outlier did not recur in this batch. Playback depended on a GUI frame even when the transport was already located and the project was ready.

After a stopped locate settles, the host prepares a single start at that exact musical position. The selected MIDI input can then submit the usual PlayClock command on the first Clock after Start/Continue, including output lead and input calibration. The host subsequently adopts the same start. Changes to the project, transport, input route or calibration invalidate the cue. An unprepared position or a busy output takes the existing host path. The audio callback and ordinary clock-pulse processing keep their existing responsibilities.

Six exact-position and two late starts per build; each delivered SPP, Continue, 144 clocks and Stop at 120 BPM through Model 12 USB MIDI → DIN OUT → UM-ONE. An independent UM-ONE listener captured the wire. Crash waveform matching covered both the 48 kHz digital loopback and the 44.1 kHz Model 12 MAIN USB return. All runs used the same unmodified eight-bar S-MU2000 session.

| First incoming Clock to | Previous head | Fixed |
|---|---:|---:|
| Playback command, all eight starts | 14.427–15.367 ms | 0.001–0.002 ms |
| Digital crash onset, six 8.000 s takes | 35.2 ms mean (32.8–39.5) | 21.3 ms mean (16.0–25.0) |
| Digital crash with diagnostic probes removed | — | 19.5 ms mean (15.3–25.2) |

The previous build sampled immediately before submission; the fixed build sampled immediately after it returned (microsecond-resolution software timestamps). In all three batches both returns had exactly one crash on each of the six 8.000 s starts and none on either 8.125 s start. Later accompaniment matched the reference in every take. The final uninstrumented build also prepares the latest grid when rapid locates leave a prior grid publication pending. On the Model 12 MAIN USB return, the six exact starts averaged 92.6 ms (90.3–97.0) before and 77.6 ms (74.5–82.9) on the final build. These measurements include the external audio return path.

The new regression went red on the previous head before the next host frame. It now exercises first-Clock dispatch, host acknowledgement without a second Play, edited-project fallback, and taking follow offline between dispatch and host acknowledgement. The original PR branch passed the mixer, playback and UI suites; the engine passed 446 with the previously reproduced Windows movie-relink path-separator failure. The same four suites on the Windows integration with #1536 and #1658 passed 1120 tests (5 ignored). The focused regression also passed twelve consecutive runs. Formatting, the asset audit, and strict Windows integration all-targets Clippy for the changed crates passed.

![Per-take MIDI Clock dispatch and recorded crash comparison](https://raw.githubusercontent.com/mtlcl410/soundcraft/8ca7cbfdcb6e902216dfdb087ecb04fc3a218d2c/docs/images/midi-clock-resume-dispatch.png)

### Digital loopback to the Model 12 MAIN return

The previous six exact starts averaged 19.47 ms from first Clock to digital loopback and 77.61 ms to MAIN USB. Matching the same crash at each tap accounts for the additional **58.14 ms**. The independent Windows capture callbacks timestamped the monitor copy 1.94 ms earlier than the digital witness. Monitor capture to ASIO output took 45.13 ms, and ASIO output callback to MAIN USB return took 14.95 ms. Inside the 45.13 ms monitor interval, the input and output callbacks containing the attack were 34.41 ms apart on average. Sample positions within those blocks account for the remaining 10.72 ms.

With the same eight-bar S-MU2000 project, executable, 120 BPM physical MIDI loop and 256-frame ASIO driver buffer, twelve new takes alternated monitor prefill settings. Each setting had four exact starts and two late starts. All times below are means from the four exact starts per setting.

| Interval | 40 ms monitor prefill | 20 ms monitor prefill |
|---|---:|---:|
| Monitor capture to ASIO output callback | 48.59 ms | 30.14 ms |
| ASIO output callback to MAIN USB return | 14.50 ms | 14.59 ms |
| Digital loopback to MAIN USB return | 61.15 ms | 43.04 ms |
| First incoming Clock to MAIN USB return | 83.15 ms | 62.49 ms |

Reducing the external monitor prefill saved **18.11 ms** between digital loopback and MAIN. As an independent check, writing the recorded crash straight to ASIO 9/10 and capturing MAIN USB 11/12 gave 14.38–15.61 ms across six repetitions (mean 14.67 ms). This last interval includes the driver, device and USB recording return. The measurement uses the driver's ADC timestamp and cannot distinguish their one-way contributions. SoundCraft had already rendered the signal at the digital tap. Its prior instrumented six takes averaged 6.05 ms to receive the playback command in the audio callback and another 4.62 ms to finish the first mix block. Those are separate runs and include scheduling.

The digital, monitor-input, ASIO-output and MAIN recordings each contained one crash in all eight 8.000 s takes and zero in all four 8.125 s takes. Later accompaniment matched on both digital and MAIN in all twelve (correlation above 0.99). Every take captured SPP, Continue, 144 clocks and Stop. The monitor logged zero short callbacks, overflow trims or ASIO status flags during the measured playback windows. Both the boundary-note and first-Clock dispatch regressions passed again. The product code and its default audio settings are unchanged in this measurement update.

![Measured MIDI Clock to audio taps and the effect of monitor prefill](https://raw.githubusercontent.com/mtlcl410/soundcraft/2b53c7e6a68dc73b7f63d798b8f8abefff8771bd/docs/images/midi-clock-main-return.png)

### Direct hardware playback from the external Clock

SoundCraft sent the same 48 kHz eight-bar S-MU2000 project directly through Model Mixer ASIO to physical outputs 9/10 (44.1 kHz, 256 frames). The local Windows build combined the Clock follower at `2b53c7e` with the Model 12 sample-format support in #1634 and hardware routing at #1635 (`7e922669`). These routing prerequisites apply to this hardware test. The original project was copied byte-for-byte and its stereo output was mapped to channels 9/10 in memory.

| First Clock at UM-ONE to crash onset on MAIN USB 11/12 | Mean (range), four 8.000 s starts |
|---|---:|
| Previous 20 ms monitor prefill | 62.49 ms (57.47–65.47) |
| Direct SoundCraft ASIO output | **28.07 ms (24.21–32.03)** |

The direct takes measured 32.03, 27.57, 28.45, 24.21 ms. Direct playback averaged **34.42 ms faster** on this setup. Both runs used the same 120 BPM physical MIDI path (Model 12 DIN OUT to UM-ONE), four exact starts, two 8.125 s starts, the same waveform threshold (0.90), and the same driver input-time adjustment (6.80 ms). The previous run recorded through the external monitor process. The driver rejected a second independent ASIO client during direct playback, so a local input-only diagnostic copied MAIN 11/12 samples from SoundCraft’s native duplex stream to a background writer. The diagnostic did not forward audio or alter playback scheduling. Results describe the recorded MAIN return across separate runs.

Direct MAIN contained exactly one crash in **4/4** exact starts and zero in **2/2** late starts. Later accompaniment was present in all six (minimum correlation 0.994). Each take captured its specified Song Position, Continue, 144 Clock pulses and Stop. The input-block sequence was continuous in every take.

![Direct ASIO and 20 ms monitor route measured on the same chorus](https://raw.githubusercontent.com/mtlcl410/soundcraft/1c8c5741cc17bf9f5abf87e4d080fae4347ffd76/docs/images/midi-clock-direct-asio.png)

### Direct ASIO buffer sizes on the Model 12

At 44.1 kHz, requesting 128 or 64 frames in SoundCraft while the TASCAM panel was set to 256 still delivered 256-frame callbacks in both directions. Changing the vendor panel and reopening the stream produced the requested sizes. The final run restored and verified 256. Two independent stream opens per setting used the same S-MU2000 project and physical Model 12 → UM-ONE MIDI loop described above.

| Actual frames (in/out) | First Clock to MAIN, mean (range) | Takes with waveform deviations | Low-level windows |
|---|---:|---:|---:|
| 256 / 256 | 27.20 ms (23.59–32.43) | 1/12 | 0 |
| 128 / 128 | 21.52 ms (18.97–26.59) | 2/12 | 1 |
| 64 / 64 | 15.33 ms (12.87–21.14) | 4/12 | 0 |

All 24 starts at 8.000 s produced one crash each. All 12 starts at 8.125 s produced zero, with later accompaniment present in every MAIN recording. The mean includes all eight exact starts per setting. We timestamped the first received Clock and matched the crash on the stereo MAIN USB return, correcting input timestamps by 6.803, 3.900 and 2.449 ms respectively. At 64 frames the mean was 11.86 ms lower than at 256 on this system.

For signal integrity we captured the native 9/10 output and MAIN 11/12 simultaneously. We aligned them once per take, fitted stereo gain, and counted takes with residual steps above 16 counts in 16-bit PCM. A low-level window is 64 consecutive samples with MAIN RMS below 20% of an expected RMS above 30 counts. At both lower sizes the first exact start after reopening showed a discrepancy. The single low-level window at 128 frames lasted 1.45 ms. These are recorded waveform deviations; audibility and their cause remain unverified. No sample clipping or gaps in the callback capture sequence were detected. Injecting a 64-frame mute and a one-sample spike into copies of a clean recording confirmed detector sensitivity. This update adds hardware evidence only.

![Measured MIDI Clock to MAIN latency by actual ASIO callback size](https://raw.githubusercontent.com/mtlcl410/soundcraft/9e4f5d8e1aeb99f86c7b440b752adfe1c7bbeefb/docs/images/midi-clock-asio-buffer-sizes.png)

### Locating low-buffer waveform changes

On the original 128-frame take, MAIN fell to 14.9 PCM counts RMS for a 64-sample window (1.45 ms), while the simultaneous level-matched 9/10 mix measured 98.4 counts. This window began 4.35 ms into the rendered crash on the whole-take alignment. Replaying those same 9/10 samples through an independent ASIO client produced a clean MAIN capture. Three equivalent replays of the flagged 64-frame takes also passed the same dropout and residual-step checks.

Fresh SoundCraft runs captured the converted samples at the ASIO callback output and timed the actual VST3 processor call. The first sounding block consumed **10.64 ms at 128 frames** (2.90 ms budget), including **10.04 ms inside S-MU2000’s `IAudioProcessor::process`**. At 64 frames the corresponding times were **7.28 / 6.78 ms** (1.45 ms budget). Both cold starts showed a MAIN waveform deviation. The specific 128-frame RMS dropout did not recur. Removing only the verse-bass VST3 assignment in a control copy preserved the four drum instruments, reduced the first 64-frame block to **0.12 ms** and yielded six clean returns. These are elapsed call times, including scheduling. The taps bound the deviation to the path between the delivered output samples and the recorded MAIN bus. They cannot identify which driver or device stage handled the late block.

Of the four earlier 64-frame flags, two were cold starts. Each of the other two recordings fits the output with one change in relative alignment (5 or 6 samples, 0.11–0.14 ms). Allowing that change reduced the peak residual step below 2.4 counts in each take. The original fixed-delay test was sensitive to timing changes as well as level changes.

The unmodified project passed **12/12** exact starts at 8.000 s (one crash each) and **6/6** late starts at 8.125 s (zero crashes, later accompaniment present) on the physical MIDI loop. The two modified-project controls are excluded from those totals. Listener assessment is pending. This verification adds a figure and evidence to the existing PR; the follower and playback defaults are unchanged.

![Rendered stereo output and MAIN return around the deviations](https://raw.githubusercontent.com/mtlcl410/soundcraft/f76cef2a4fbd17d04997fc6164e6685c3da3cded/docs/images/midi-clock-asio-waveform-detail.png)

## Open questions

- Q-10. Should the MTC Reader eventually use the same MIDI input sample offset? This revision applies it only to external Beat Clock follow.
- Q-16. Should the Setup › MIDI › Sync menu entry be renamed? This revision keeps the existing name and takes the user directly to the external clock controls.

## Known limits and deferred work

The project tempo map cannot yet be written from incoming clock as a tempo-record pass. Bridge software is supplied by the user. Continuous MTC chase, MMC, a loopback calibration assistant, OS-timestamped sends and Windows MIDI Services remain separate work.

## Review and merge order

#1536 → #1662 → #1663 → **#1669**. The prerequisite branches live on the contributor fork. Review the [clock-follow increment over #1663](https://github.com/mtlcl410/soundcraft/compare/feat/g11-mtc-generate-chase...feat/g11-external-clock-follow). Refresh this draft from main after #1663 lands. Tracks #1661.
