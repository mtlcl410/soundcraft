<!-- storage-output-timing -->
## Shared device timing after USB STORAGE

This draft incorporates #1662's output timing recovery through #1663. The external Beat Clock path distinguishes unknown output latency from a measured zero. A pending Continue waits for timing, and a subsequent Stop or locate cancels the superseded start. An armed external Clock start also prevents a stream handoff. Local playback and the existing recording loss policy retain their own transport handling.

Windows verification with #1536 applied at `74f7305`: 1,675 tests passed across four crates, five were ignored by default, and the previously reproduced AAF locator failure remained (#1658). All-targets strict Clippy passed. The ignored eight-hour Clock simulation passed when run separately. The three physical STORAGE cycles exercised MTC on #1663. The external Clock safeguards on this branch were verified in software. [Hardware measurements and absolute-offset comparison](https://github.com/storytold/soundcraft/pull/1663).

Once recovery succeeds, the UI clears its obsolete idle-device warning if it is still current. It preserves subsequent messages and the history of an interrupted recording. The UI regression failed before that change and passed after it.

At the earlier head `67b3e50`, the complete Windows UI suite passed 408 tests with one default skip. Strict UI Clippy passed with the Windows prerequisite. Playback, mix and engine trees match the four-crate test run above.
<!-- end-storage-output-timing -->

SoundCraft can play and record against an external sequencer’s MIDI Beat Clock. Start, Continue, Stop and Song Position Pointer follow the source on a live beat grid while preserving the saved project tempo. [Setup and recording guide](https://github.com/mtlcl410/soundcraft/blob/69eadb83a15561d213b3fb25bb24fcf7cf3d9ca6/docs/midi-input.md#follow-midi-beat-clock)

Part of #1661. Fixes #1674. Fixes #1675.

Audio and MIDI can be recorded together. **Coast** keeps the take open through clock loss and re-lock. **Stop on loss** finalizes both tracks at timeout. MTC Online in #1663 uses absolute timecode and rolls on the local sample clock after a locate. A new locate can displace an open take, so MTC recording requires going offline.

**Eight-bar playback under external Clock.** Existing MIDI clips on tick-based tracks now retain their musical start and end on the temporary playback grid. The saved session retains its original tempo and bounds. The Model 12 drove the same S-MU2000 arrangement at 120 and 100 BPM. Both the digital accompaniment and MAIN contained all eight snares at each tempo and one chorus crash. Before the fix, 100 BPM yielded five snares on both paths. [Eight-bar hardware results](https://github.com/mtlcl410/soundcraft/blob/5b1418a8166d872adcf0107b2770662e9acaf7f4/docs/model-12-clock-follow-hardware.md#eight-bar-accompaniment-at-120-and-100-bpm)

The same symptom during ordinary session tempo edits reproduces on main at 85623f2. [PR #785](https://github.com/storytold/soundcraft/pull/785) covers those edits and can land independently of the G-11 stack. [Issue #1690](https://github.com/storytold/soundcraft/issues/1690) provides the hardware-independent reproduction. The same instrument-render regression produced 5/8 snares at 100 BPM on main and 8/8 on #785 (`a278c26f`), including a successful undo/redo check there. This draft changes the external-clock playback path only for this fix.

**Tempo changes during performance.** With two SoundCraft instances linked through Model 12 DIN and UM-ONE, the follower played all 64 eighth notes against the leader’s 32 beats. At the chorus, four consistent Clock intervals now trigger a fresh tempo estimate and let the future beat grid update promptly. Across three takes per direction, the first full beat after a 120 → 100 BPM change was 28–42 ms early (previously 99 ms early). At 100 → 120 BPM it was 25–33 ms late (previously 59 ms late). The final four beats returned within 4.05 ms of the verse offset. Both chorus-resume checks still passed. Windows playback and UI library suites passed 631 tests in total, with the eight-hour simulation also passing separately. [Signal path, before/after plot and regression](https://github.com/mtlcl410/soundcraft/blob/d1545d2c00b80d0cde746d8d37b53e524175f5b5/docs/model-12-clock-follow-hardware.md#changing-tempo-at-the-chorus)

### External Clock tempo steps (af4af80b)

On the same 24-bar 80→130→80 BPM score, the first offbeat at the slowdown moved from **70.104 ms early to 0.000 ms**. The maximum absolute error across that final section fell to **0.167 ms**. All 192 hats, 48 kicks and 48 snares sounded with complete final bursts. The existing 12-bar hardware results below remain measurements of an earlier revision.

At af4af80b the sequencer released events through the last received F8 plus one pulse. The device-buffer exception verified below applies to the current revision. At a confirmed tempo change it joins the new pulse grid after committed audio. Sustained changes of at least 8% qualify; large, coherent steps of at least 30% can qualify in two intervals. The normal jitter filter and the running audio sample rate are preserved.

On Windows, the previous head `49a85d8e` failed both the online PCM matrix and the render-ahead test. The replacement for `chorus_tempo_step_keeps_the_next_backbeat_within_one_clock` checks every eighth, the unchanged boundary, onset count, per-sample waveform and final silence. The 128↔140 BPM controls passed at four sample rates (peak 0.042 ms). Coast relocked after 300 ms on F8 alone, with 65/65 hits and the last +2.458 ms. The eight-hour flutter peak stayed at 148 samples and all nine steady-tempo BPM/phase p95 pairs matched the baseline. Local library tests passed (102 mix, 228 playback, 412 UI), plus the explicit eight-hour profile and Clippy for those three crates. [PCM regression and reproduction code](https://github.com/mtlcl410/soundcraft/blob/af4af80b626bab785de97ba895f76187b76da99d/crates/ui-egui/src/app/clock_follow/tests/large_steps.rs)

<details>
<summary>Signed PCM onset deviations for the first eight beats</summary>

48 kHz, ideal input, at most 128 samples per render, with a 30 ms guard for grid edits. F8 at index 384 is a bar line; index 396 is halfway through a beat. Negative means early and positive means late. Counts include the lead-in. Tolerances are 10 ms for the first offbeat and 4 ms from the second beat. These values measure software rendering; loudspeaker and USB latency require a separate capture.

| BPM | Pulse | Attacks | Signed ms at the transition, then every half beat through +8 beats |
|---|---:|---:|---|
| 130→80 | 384 | 49 | 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 |
| 130→80 | 396 | 50 | 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 |
| 120→100 | 384 | 49 | 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 |
| 120→100 | 396 | 50 | 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 |
| 180→60 | 384 | 49 | 0, 0, 0, +0.021, +0.021, +0.021, +0.021, +0.021, +0.042, +0.042, +0.042, +0.042, +0.042, +0.042, +0.062, +0.062, +0.062 |
| 180→60 | 396 | 50 | 0, 0, 0, 0, 0, 0, -0.021, -0.021, -0.021, -0.021, -0.021, -0.021, -0.021, -0.021, -0.021, -0.021, -0.042 |
| 100→120 | 384 | 49 | 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -0.021, -0.021, -0.021, -0.021, -0.021, -0.021 |
| 100→120 | 396 | 50 | 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -0.021, -0.021, -0.021, -0.021, -0.021, -0.021 |
| 80→130 | 384 | 49 | 0, -0.021, -0.021, -0.021, 0, 0, 0, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021 |
| 80→130 | 396 | 50 | 0, -0.021, -0.021, -0.021, 0, 0, 0, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021, +0.021 |
| 60→180 | 384 | 49 | 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, +0.021, +0.021, +0.021 |
| 60→180 | 396 | 50 | 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, +0.021, +0.021, +0.021 |

</details>

Avid documents transmitting Beat Clock, per-port playback offsets, and measuring the recorded response. SoundCraft's external-follow thresholds above are project acceptance criteria. [Pro Tools Reference Guide 2026.4, printed pp. 743–744](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf#page=845)

**Earlier three-section hardware run (6b82d9b).** On a 12-bar 80 → 130 → 80 BPM performance, all 48 kicks and 96 hi-hats landed in their expected slots. The next beat after slowing was 26–37 ms early across three takes (previously 113–128 ms early). The first offbeat after slowing still arrived 102–126 ms early. After speeding up, the next beat was within 7 ms of the verse offset. Windows playback and UI library suites passed 633 tests, and the eight-hour simulation passed separately. [Transition measurements and plot](https://github.com/mtlcl410/soundcraft/blob/6b82d9bc84af17b259b98970dc5557a93c80d7a0/docs/model-12-clock-follow-hardware.md#three-section-dance-track-at-80-130-and-80-bpm)

**Verification**

- At `5b1418a8`, both external-tempo regressions passed. Across the four affected Windows library suites, 1,213 tests passed and five were ignored by default. The movie-relink path test also failed on unchanged upstream main. Formatting and all-targets Clippy for the four affected crates completed; Clippy emitted existing warnings. These are local results.

- **Hardware.** On the Model 12 → UM-ONE loop, the S-MU2000 chorus crash sounded once at 8.000 s and zero times at 8.125 s, with the later accompaniment intact. At 256 frames, direct ASIO 9/10 averaged 28.07 ms from first Clock to MAIN USB, compared with 62.49 ms through the 20 ms monitor prefill. [Hardware acceptance report and comparison figures](https://github.com/mtlcl410/soundcraft/blob/717f96953313c385ee2acf24a1b0aedeb7672585/docs/model-12-clock-follow-hardware.md)
- **Windows, simulated recording.** At `ed7ae31`, the Coast and Stop-on-loss regressions decoded the take WAV and checked the committed MIDI notes. The MTC Online recording guard also passed. Playback/UI libraries and MIDI-input integration tests passed 584 tests, with five ignored. Workspace formatting and all-targets Clippy for both changed crates passed.
- **First note on Continue (#1674, Windows software regression).** The same 48 kHz / 120 BPM session counted instrument Note Ons at three starts (7.500, 8.000 and 8.125 s). Local Play delivered the 8.000 s crash **1 / 1 / 0** times on main (`85623f2`), the pre-fix branch (`2aa39ff`) and this revision (`717f969`). External SPP → Continue → Clock delivered **1 / 0 / 0** before the fix and **1 / 1 / 0** here with an input offset of −1,440 samples (−30 ms). The later 8.500 s note played exactly once on every supported start. Main has no external Clock-follow input. The old Continue path discarded the requested musical origin when compensating the render cursor, so the fix belongs in this PR. [Pre-fix transport](https://github.com/mtlcl410/soundcraft/blob/2aa39ffc241a98a74bf7a2db52403c7f429d6b0e/crates/ui-egui/src/app/clock_follow.rs#L181-L194) · [Fix and permanent regression test](https://github.com/storytold/soundcraft/pull/1669/commits/baab55eef9b05e51c452437afb08c81c7fb22716)

<!-- manual-review-1669 -->
**Manual review and verification**

CodeRabbit’s [sixth incremental review](https://github.com/storytold/soundcraft/pull/1669#pullrequestreview-6005988643) examined `3262658`. Commit [29236b9](https://github.com/storytold/soundcraft/pull/1669/commits/29236b97d62e48cbffe013853903375456e6a03d) fixes its five inline findings and the additional overdub Undo case. MIDI notes and controllers retain their stored and followed timing across edits, including sample-boundary consolidation, edits to indistinguishable notes by index, and undoing overlapping recordings.

[e43742e](https://github.com/storytold/soundcraft/pull/1669/commits/e43742e1d822312dbe371d4593bc74215ef5f6e3) serializes a prepared Continue with concurrent edits and keeps the first audible block’s Clock data available to a late MIDI output. [Concurrent dispatch regression](https://github.com/storytold/soundcraft/pull/1669#discussion_r4653267961)

[Latest correction 69eadb8](https://github.com/storytold/soundcraft/pull/1669/commits/69eadb83a15561d213b3fb25bb24fcf7cf3d9ca6). Eleven accepted tempo updates follow an initial buffer, before a MIDI destination connects. On e43742e playback reached the seventh buffer with generation 6 cached instead of 7. The extended regression polls the output throughout all twelve buffers. It verifies each buffer’s session identity and emitted Clock, the initial Start/Clock deadline, zero backlog drops, and release of all eleven older session references. This also passes when a normal session is replaced before the destination connects. A separate regression fills the ten-slot audio snapshot pool: a delayed destination retains the grids it still needs, and a host retry can reclaim them once the inactive route has drained. The audio callback retains its fixed presentation ring. [Review discussion](https://github.com/storytold/soundcraft/pull/1669#discussion_r4653272960)

Earlier Windows checks at `69eadb8`, with prerequisite #1536 applied locally: 1,654 tests passed. The AAF locator test also fails on clean pre-review commit 717f969 (#1658). Five tests are ignored by default; the eight-hour Clock simulation passed separately. Strict Clippy passed on all targets of the four affected crates. Model 12 hardware results above are from earlier runs. GitHub workflows awaiting approval: [CI](https://github.com/storytold/soundcraft/actions/runs/44917580109) · [Nix](https://github.com/storytold/soundcraft/actions/runs/44917580115) · [SonarCloud](https://github.com/storytold/soundcraft/actions/runs/44917580117). The sixth incremental CodeRabbit review examined 3262658. That review follow-up was published at 69eadb8. GitHub shows **0 unresolved review threads out of 38**.

**Stack and scope.** #1662 supplies Beat Clock output, #1663 supplies MTC generation/chase, and #1669 supplies external Beat Clock follow under #1661. #1674 and #1675 cover Continue and startup latency. Comparing with #1663 excludes the workspace dependency pin and MTC overlap helper. The live beat counter, recording edits and the pt-BR Clock input/calibration/loss-policy and port-conflict messages belong to the follow feature. Attribution credits the linked hardware figures. [Changes relative to #1663](https://github.com/mtlcl410/soundcraft/compare/feat/g11-mtc-generate-chase...feat/g11-external-clock-follow).
<!-- end-manual-review-1669 -->

### External Clock under jitter, tempo ramps and device buffering

At 48 kHz, all 1,782 eighth notes in the 36 tempo-step cases retained a single complete PCM waveform. The first offbeat peaked at 6.604 ms with ±1 ms input jitter and 5.875 ms with ±2 ms. Later peaks were 4.750 and 4.188 ms. Across four ten-minute steady packet-burst runs there were zero false steps, dropouts or onset errors. Grouped 180→60 BPM input remains a limitation: a subsequent eighth sounded up to 196.896 ms early.

Continuous ±8% pitch-fader moves improved from 9.0625 to 3.8333 ms peak. All nine steady p95 pairs and the original 12 ideal-input vectors matched the previous head. The eight-hour grid peak remained 148 samples; a separate eight-hour audio render produced identical records for all 115,201 attacks (234-sample peak). The slow 124.0→124.3 BPM drift triggered neither response mode. The largest consecutive BPM change after acquisition was 0.09139 BPM.

When the device buffer is shorter than a pulse, both policies render sample-identical output. In the ten eligible steady conditions, scheduling to the measured device deadline reduced late attacks from +28.646…+85.104 ms to zero samples. The 18-condition slowdown sweep checked 58,752 note and click attacks across both policies. A separate red regression reproduces an entire overdue note disappearing on return to prediction; all waveform and release checks now pass. [PCM tables, signed errors and reproduction commands](https://github.com/mtlcl410/soundcraft/blob/614be5667ef9581ab01ea5c6c858f029c9ba2649/docs/external-clock-response-measurements.md)

## Coast recovery when the external clock returns

In `82cc19c6`, a rolling Coast transport relocks when returning F8 pulses establish a valid tempo. It estimates the nearest musical pulse from the previous clock and corrects the writable grid without restarting playback or seeking in an open take. A lone tick does not establish a new tempo. Stop on loss remains stopped until the source sends Start or Continue followed by Clock. F8 alone carries no absolute song position.

| Same 48 kHz rendered eighth-note backing, 120 → 128 BPM, source returns at 8.300 s | Before | After |
|---|---|---|
| Coast | 65/65 attacks; still Coasting; last attack +473.438 ms | Locked at 128.000 BPM; 65/65 distinct attacks, no transport restart; last attack +2.458 ms (118 samples) |
| Stop on loss | Stopped at sample 390,563; 33 attacks | Same stop sample and 33 attacks; F8 alone did not restart playback |

Ownership checked against upstream main `85623f28`: that revision has no external Beat Clock follow command or reader. Re-ran the original A-3 reproducer on the old and corrected code. The committed PCM regression counts the full rendered attacks, pairs each with its own grid position, and checks both loss policies. This is a software measurement using the production mixer and sampler.

The first hat after F8 returned was 200 samples early (4.167 ms); all subsequent attacks were within 185 samples (3.854 ms). Across both affected crates, 942 tests passed and five were ignored. Workspace format and all-targets Clippy passed. An additional Windows run with all warnings promoted to errors stops at the existing unused `mut` in `crates/engine/src/autosave.rs:481`; that file is byte-identical on main, the previous PR head, and this commit.

## Known limits

At 44.1 kHz and 256 ASIO frames, 1 of 12 takes showed a residual step between the ASIO 9/10 output and MAIN USB 11/12. The cause is unknown. All 12 passed the low-level check. The 40 near-silent samples at 13.498 s occurred in a separate 64-frame run. [Investigation and waveform comparison (#1686)](https://github.com/storytold/soundcraft/issues/1686)

**Merge order.** #1536 → #1662 → #1663 → **#1669**. This PR stays in draft until its prerequisites land. [Review the changes over #1663](https://github.com/mtlcl410/soundcraft/compare/feat/g11-mtc-generate-chase...feat/g11-external-clock-follow)

## A-10 verification after output timing loss

The integrated branch inherits the Clock fix from #1662 and the MTC fix from #1663. The same regressions on upstream main had no output implementation to exercise.

At 48 kHz and 120 BPM, a deterministic port polled every 1 ms lost output timing from 100 to 200 ms. Previously it delivered five expired clocks, starting 95.833 ms late, with four successive 1 ms intervals. After the fix the first F8 was due at 208.333 ms and handed off at 209 ms (+0.667 ms). Five owed ticks were spread over the next beat: 29 clocks from 209 to 688 ms, at 17–18 ms intervals (28 intervals). In order, intervals 6, 15 and 24 were 18 ms; all other intervals were 17 ms. At 700 ms the pulse count matched uninterrupted playback; subsequent handoffs matched it exactly. Both runs sent 49 clocks through 1000 ms inclusive, with identical transport commands. A 200 ms gap also finished at 49/49. These are simulated MIDI handoffs.

At 25 fps, after timing was unknown from 100 to 200 ms, the old first QF was 100 ms late. The fix sends one full-frame locate at 200 ms for 00:00:00:05, skips the obsolete pieces, and starts the next complete QF group at 240 ms. Piece 0 reached the simulated port at its deadline (+0 ms), followed by pieces 1–7 every 10 ms. The 40 ms wait is the time to the next group boundary. A separate 20–50 ms gap verifies a live locate even close to the transport origin.

Local Windows playback suite: 227 passed. Workspace rustfmt and playback Clippy (all targets, warnings denied) passed. Merge order: #1662 → #1663 → #1669.

## Open questions

- Does the current Coast behavior suit a live change of clock source? Since 82cc19c, a rolling transport relocks to the tempo and relative phase of returning F8 pulses once a valid tempo is available, without waiting for Start/Continue. Stop on loss stays stopped on F8 alone.

<!-- g11-scenario-audit-20261122 -->
### Unattended performance and studio scenarios

- Should tempo-follow response be fixed or user-adjustable? The measured ±8% ramp peak is 3.8333 ms, while the unchanged clean step cases remain within one sample on the first offbeat and three samples from the second beat. Packed delivery can take 7 or 15 F8s to confirm and reach 196.896 ms early. Bitwig offers a response slider for this trade-off. [Bitwig Studio User Guide, Dashboard › Synchronization Settings](https://www.bitwig.com/userguide/latest/the_dashboard/)
- Is this bounded policy acceptable on large device buffers? Previously committed PCM cannot be recalled when the clock slows. In the 20% slowdown sweep, the earliest first offbeat and next beat were −25.000 ms, already committed before the missing pulse could be observed. After falling back to the one-pulse wire limit, the latest first offbeat was +86.500 ms and the next beat +83.771 ms (300 BPM / 2,048 frames / 50 ms). The amount of late fallback error depends on the policy and device. Short buffers retain the hard limit even with a long lead. [PCM tables, signed errors and reproduction commands](https://github.com/mtlcl410/soundcraft/blob/614be5667ef9581ab01ea5c6c858f029c9ba2649/docs/external-clock-response-measurements.md)
- Should a local playback loop be ignored while following an external position? Inside/outside Continues started at 36,000/120,000 samples and both had no active local loop. Should SPP during playback remain ignored?
- Should plugin reset on Stop have to emit individual note-offs as well? All 100 notes released, 42 through reset. What tempo-history retention is appropriate over longer sets? The count grew from 529 at one hour to 2,703 at six hours. Should malformed follow preferences be recovered individually?
- Local long-run command after applying the scenario overlay: `cargo test -p soundcraft-ui-egui --lib scenario_a6_six_hours_of_seeded_steps -- --ignored --nocapture --test-threads=1`.

[Measurements and local regression names](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7070845420)
<!-- /g11-scenario-audit-20261122 -->

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->
<!-- coderabbit-ai-generated:v1 -->

## Summary by CodeRabbit

* **New Features**
  * Added MIDI Beat Clock output and external clock following, with device routing, timing offsets, clock-loss settings, and synchronization diagnostics.
  * Added MIDI Time Code generation and chase playback, with timecode, input/output, and freewheel controls.
  * Added session options for timecode start, external offsets, and preserving clip positions or timecodes when changing the start time.
  * Added transport position entry and selection-boundary dialogs, plus clickable selection counters.
* **Bug Fixes**
  * Improved timecode parsing and validation, including errors for positions before the session start.
  * Improved MIDI recording alignment on temporary tempo grids and preserved captured timing through clip edits.
  * Prevented recording while MTC chase is online.
* **Documentation**
  * Updated synchronization guidance and hardware notes; hardware verification remains pending.
<!-- end of auto-generated comment: release notes by coderabbit.ai -->