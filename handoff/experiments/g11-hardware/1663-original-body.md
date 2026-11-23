Tracks the MIDI Time Code generator and chase part of #1661.

## Behaviour

Setup › Playback Engine selects the MTC output or an input to follow online. The generator sends full-frame SysEx on stopped locates and quarter-frame messages during playback at 24, 25, 29.97 drop-frame and 30 fps. The chase reader follows a selected input, preserves a stopped locate into the first roll, and stops on loss of timecode. Acquisition uses the presented audio position to trim transport speed. The two sides of a crossfade advance at the rates used to render their own buffered samples.

## Hardware acceptance

- **Generator.** SoundCraft USB MIDI → TASCAM Model 12 MIDI OUT → Roland UM-ONE → independent capture on Windows. At 30 fps all five stopped locates returned the expected full-frame messages with zero quarter frames while stopped. At 24, 25 and 29.97 DF, 15 more locates and four rolling boundary tests passed. The drop-frame label advanced from `00:00:59;29` to `00:01:00;02` and from `00:09:59;29` to `00:10:00;00` on adjacent stopped positions.
- **Chase.** Model 12 recorder MIDI OUT → UM-ONE → SoundCraft, with a 48 kHz S-MU2000 instrument session. A stopped locate reached sample 240,000 (5.000 s). The first note was A4, followed by F♯5 after 0.50273 s. At the 17 s checkpoint, the recorded endpoint onset was 2.86 ms behind the external timecode. All 20 expected attacks were present. There was no replay of the earlier C4 or new attack after the last timecode; recording continued for 3.512 s after stop.
- **Pitch.** Compared the 19 notes common to the hardware take and local playback, using 3,344 waveform-aligned windows per take. The previous 12 s G4 window measured +8.49 cents by FFT and +9.67 by period. The same window now measured −0.001 and −0.081 cents. The largest same-direction change corroborated by both methods was about 2 cents. The separate absolute maxima across all windows were 3.14 cents by FFT and 6.30 by period at different attacks. These are short-window observations on this setup.

## Regression coverage

The G4 regression first failed on the old code at 9.426 cents during a 1.025× to 1.013× rate transition. It passes the 2-cent limit with the fix. Tests also cover quarter-frame order and timeouts, drop-frame boundaries, first roll after a locate, stopped seeks, discontinuities and retention of the original pitch across chase speeds. The standalone Windows branch passed all 519 library tests (120 playback, 50 DSP and 349 UI) with `cargo test --locked -p soundcraft-dsp -p soundcraft-playback -p soundcraft-ui-egui --lib --no-fail-fast`. Workspace formatting passed. The pitch-preservation regression also passed separately after addressing two strict-Clippy findings in its test code.

The standalone Windows `cargo xtask ci` passed formatting and stopped at workspace Clippy on the existing engine findings in `autosave.rs` (unused mutable builder) and `io.rs` (unused Unix test helper). Both are addressed by #1536. In a separate integration checkout containing #1536 and both G-11 changes, Clippy passed for model, DSP, playback and UI with all targets and warnings denied. The same checkout passed 525 library tests (1 model, 50 DSP, 124 playback and 350 UI).

## Review and merge order

This branch targets upstream main and can be reviewed without #1662. Both feature branches use the same published craft-libs revision. Draft pending #1536 for the Windows workspace gate. Recommended landing order is #1536 → #1662 → this PR. Refresh this branch after #1662 lands so the shared Player play path sends Beat Clock transport for either start mode, and stopping clears the presented position and notifies the clock worker. Keep #1661 open until both features land.

