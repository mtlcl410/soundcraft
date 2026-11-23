Tracks the Beat Clock output part of #1661.

## Behaviour

Setup › MIDI › MIDI Beat Clock selects a named output, enables transmission and saves a signed sample offset with the session. Positive offsets delay the clock. The worker derives 24 pulses per quarter note from the session tempo map and the audio transport. It sends Start at zero, Song Position Pointer and Continue on a nonzero start, and Stop when playback ends. MIDI device I/O runs outside the audio callback. Windows, macOS and Linux use native MIDI ports.

## Hardware acceptance

On Windows, a 48 kHz SoundCraft session at 120 BPM sent MIDI through a physical loop, captured independently at a Roland UM-ONE input. Starting at zero produced Start, 169 clock pulses and Stop (120.09 BPM measured). Restarting at sample 48,000 produced Song Position Pointer 8 (`F2 08 00`), Continue, 63 clocks and Stop (120.61 BPM measured). The check decoded the bytes and estimated the tempo separately for each run. Tempo changes and delayed starts were exercised in software. The hardware check covers this Windows path.

## Regression coverage

The playback regressions check 48 clocks at 120 BPM and 24 at 60 BPM over equal one-second spans, a mid-song locate, cancellation of a delayed start, and bounded interpolation when the audio device stalls. On Windows, the standalone branch passed all 450 library tests (1 model, 107 playback and 342 UI) with `cargo test --locked -p soundcraft-model -p soundcraft-playback -p soundcraft-ui-egui --lib --no-fail-fast`. Workspace formatting passed. The original wire capture was decoded again for this PR.

The standalone Windows `cargo xtask ci` passed formatting and stopped at workspace Clippy on the existing engine findings in `autosave.rs` (unused mutable builder) and `io.rs` (unused Unix test helper). Both are addressed by #1536. In a separate integration checkout containing #1536 and both G-11 changes, Clippy passed for model, DSP, playback and UI with all targets and warnings denied. The same checkout passed 525 library tests (1 model, 50 DSP, 124 playback and 350 UI).

## Review and merge order

This branch targets upstream main and contains the Beat Clock feature alone. Its MIDI encoding dependency is pinned to a commit already in upstream craft-libs. It is independently reviewable from the MTC feature. Draft pending the Windows workspace gate tracked in #1535 and fixed by #1536. Merge #1536 first, then Beat Clock after the gate passes. Then refresh #1663 to reconcile the shared Player start/stop paths before merging MTC. Keep #1661 open for both deliverables.
