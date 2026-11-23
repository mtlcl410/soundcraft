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

**Three-section dance track.** On a 12-bar 80 → 130 → 80 BPM performance, all 48 kicks and 96 hi-hats landed in their expected slots. The next beat after slowing was 26–37 ms early across three takes (previously 113–128 ms early). The first offbeat after slowing still arrived 102–126 ms early. After speeding up, the next beat was within 7 ms of the verse offset. Windows playback and UI library suites passed 633 tests, and the eight-hour simulation passed separately. [Transition measurements and plot](https://github.com/mtlcl410/soundcraft/blob/6b82d9bc84af17b259b98970dc5557a93c80d7a0/docs/model-12-clock-follow-hardware.md#three-section-dance-track-at-80-130-and-80-bpm)

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

## Known limits

At 44.1 kHz and 256 ASIO frames, 1 of 12 takes showed a residual step between the ASIO 9/10 output and MAIN USB 11/12. The cause is unknown. All 12 passed the low-level check. The 40 near-silent samples at 13.498 s occurred in a separate 64-frame run. [Investigation and waveform comparison (#1686)](https://github.com/storytold/soundcraft/issues/1686)

**Merge order.** #1536 → #1662 → #1663 → **#1669**. This PR stays in draft until its prerequisites land. [Review the changes over #1663](https://github.com/mtlcl410/soundcraft/compare/feat/g11-mtc-generate-chase...feat/g11-external-clock-follow)

## Open questions

<!-- g11-scenario-audit-20261122 -->
### Unattended performance and studio scenarios

- Should a rolling Coast session relock on F8 alone when the replacement source sends no Start/Continue? The last of 65 attacks was 473.438 ms late. Should the proposed ramp and deck-change targets be accepted? The ±8% sweep peaked at 9.062 ms; the 130→80 section of a complete EDM song peaked at 70.104 ms.
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