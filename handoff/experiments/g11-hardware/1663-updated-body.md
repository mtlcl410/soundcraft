Tracks the MIDI Time Code generator and chase part of #1661.

## Behaviour

Setup › Playback Engine selects the MTC output or an input to follow online. The generator sends full-frame SysEx on stopped locates and quarter-frame messages during playback at 24, 25, 29.97 drop-frame and 30 fps. The chase reader follows a selected input, preserves a stopped locate into the first roll, and stops on loss of timecode. Acquisition uses the presented audio position to trim transport speed. The two sides of a crossfade advance at the rates used to render their own buffered samples.

## Hardware acceptance on the pre-review build (e27e3f1)

These measurements are the original physical baseline. Hardware verification on the revised build is pending.

- **Generator.** SoundCraft USB MIDI → TASCAM Model 12 MIDI OUT → Roland UM-ONE → independent capture on Windows. At 30 fps all five stopped locates returned the expected full-frame messages with zero quarter frames while stopped. At 24, 25 and 29.97 DF, 15 more locates and four rolling boundary tests passed. The drop-frame label advanced from `00:00:59;29` to `00:01:00;02` and from `00:09:59;29` to `00:10:00;00` on adjacent stopped positions.
- **Chase.** Model 12 recorder MIDI OUT → UM-ONE → SoundCraft, with a 48 kHz S-MU2000 instrument session. A stopped locate reached sample 240,000 (5.000 s). The first note was A4, followed by F♯5 after 0.50273 s. At the 17 s checkpoint, the recorded endpoint onset was 2.86 ms behind the external timecode. All 20 expected attacks were present. There was no replay of the earlier C4 or new attack after the last timecode; recording continued for 3.512 s after stop.
- **Pitch.** Compared the 19 notes common to the hardware take and local playback, using 3,344 waveform-aligned windows per take. The previous 12 s G4 window measured +8.49 cents by FFT and +9.67 by period. The same window now measured −0.001 and −0.081 cents. The largest same-direction change corroborated by both methods was about 2 cents. The separate absolute maxima across all windows were 3.14 cents by FFT and 6.30 by period at different attacks. These are short-window observations on this setup.

## Review fixes and regression coverage

- The MTC wire rate alone cannot distinguish 24 from 23.976, or 30 from 29.97 non-drop. Chase now uses the matching pull-down session rate for those two pairs, including the session start offset. A one-hour-offset 29.97 ND locate at 01:00:10:00 previously landed at 307,200 samples. It now lands at 480,480 samples (10.010 s at 48 kHz). The regression covers locate and roll at both pull-down rates and ordinary 30 fps. Generator rates remain 24, 25, 29.97 DF and 30.
- Generator deadlines include the audio backend’s reported playback lead and each chunk’s offset within the device buffer. Tests inject a 30 ms lead and split a callback into two chunks. At the receiving end, piece 7 represents 1¾ frames past the label. A generator-to-reader software loop checks position to within one sample at the four supported generator rates.
- Once chase locks, the audio callback applies one correction per new timecode group and stops on loss even if the UI stalls. Initial acquisition and stopped locates still use the UI. Recording or local transport takes chase offline and clears pitch-processing latency. The Options menu, transport button and desktop control command share the same Online state and validation.
- Generator packets use a bounded, preallocated, single-producer/single-consumer queue. The audio thread does not wait for the MIDI port. A saturated queue resumes with a full-frame locate and a fresh group. The output worker polls at up to 1 ms while active and 10 ms when idle. Online waiting no longer requests a full UI repaint every 15 ms.
- The crossfade still uses each grain’s own playback rate. Reapplying the review’s temporary pitch change reproduces the G4 failure at 9.426 cents. The corrected trajectory passes the 2-cent regression. A synthetic device test with no repaints after acquisition retains the first attack at the 5 s score position, measures 0.497 s to the second attack, and is 90 samples (1.875 ms) behind at the 17 s checkpoint. Loss of timecode stops playback. This test uses generated audio, a simulated device clock and a 25 ms presentation lead.
- Updated the user and agent guides, status/error translations and roadmap history. Kept the shared craft-midi-sync revision aligned with #1662.

## Windows verification and performance

The standalone branch passed 527 library tests (50 DSP, 126 playback, 351 UI), workspace formatting and the UI’s wasm32-unknown-unknown build check. In a separate integration checkout containing #1536 at 9555b196 and #1662 at d09c75e, all 538 library tests passed (50 DSP, 136 playback, 352 UI). Strict Windows Clippy passed for engine, DSP, playback and UI, including all targets. The combined transport test checks that a stopped locate emits no Beat Clock, a chased start sends Song Position Pointer and Continue, and the clock publisher uses the trimmed playback rate.

Three alternating Windows comparisons against e27e3f1 used the native output worker, an in-process MIDI sink, a simulated 30 ms presentation lead and 360 quarter-frame messages per frame rate per run. Values below are medians across three runs. Output lateness and interval error are the P95 within each run.

| Measurement | Before | After |
| --- | ---: | ---: |
| Empty-session callback, generator on, 64 frames | 1.819 µs | 1.950 µs |
| Empty-session callback, generator on, 2048 frames | 47.675 µs | 50.838 µs |
| Output lateness, 24 / 30 fps | 1.684 / 1.471 ms | 1.680 / 1.472 ms |
| Absolute interval error, 24 / 30 fps | 1.617 / 1.143 ms | 1.610 / 0.872 ms |

The larger-buffer callback median rose by 3.16 µs. With the generator off it rose from 47.325 to 49.825 µs. Windows scheduling varied across runs. This measures an empty project and software delivery. Loaded-session CPU, idle power, physical MIDI-to-audio alignment and the post-review Model 12/S-MU2000 take still need separate measurement.

## Review and merge order

The MTC branch targets main and is independently reviewable. Keep this PR in draft for the existing standalone Windows engine Clippy findings addressed by #1536. Recommended landing order is #1536 → #1662 → #1663. The combined checkout is local. After #1662 lands, refresh #1663 using the tested integration: keep both play modes in the shared start path, publish Beat Clock locates for either mode, wake its worker on transport changes, preserve the MTC presented-position reset, and initialize that field in the Beat Clock test fixture. Keep #1661 open until both features land.
