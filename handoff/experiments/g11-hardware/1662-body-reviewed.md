Tracks the Beat Clock output part of #1661.

## Behaviour

Setup › MIDI › MIDI Beat Clock saves the exact destination name and a signed sample offset. Positive offsets delay output. Start is sent at the offset-adjusted origin. For a nonzero start, seek or loop wrap, the receiver gets Song Position Pointer (SPP) and Continue. The first F8 plays on the addressed sixteenth. An off-grid locate waits for the next sixteenth. A fresh locate beyond the 14-bit SPP limit reports an error and suspends clock output until a representable locate. An uninterrupted pass can continue past that limit.

The worker follows the transport position and pass applied by the audio callback, bounded to the current device buffer. Edits that change elapsed beats reposition the receiver. Tempo changes already in the playback map retain continuity. The native worker handles MIDI I/O and reconnection. Setup displays open and send failures, ambiguous device names and unrepresentable positions. Long names and surrounding spaces round-trip.

## Hardware acceptance

The original Windows 48 kHz, 120 BPM physical loop ran from SoundCraft through the Model 12 to a Roland UM-ONE input. Start produced 169 pulses and Stop (120.09 BPM). Starting at sample 48,000 produced SPP 8, Continue, 63 pulses and Stop (120.61 BPM). The saved input timestamps give interval SD of 1.296 and 1.640 ms respectively. The corrected worker has host-side timing measurements below. A new physical capture of this revision at 120 and 180 BPM remains outstanding.

## Windows timing after review

Three five-second passes per version and tempo used the same 10 ms simulated audio callbacks, optimized test profile, and in-process timestamp sink. Run order alternated. Each cell is the median across passes. SD measures clock-to-clock intervals. P95 measures absolute deviation from the ideal interval. The first two intervals of each pass were excluded.

| Tempo | Interval SD, old → new | P95 absolute interval error, old → new | Worker iterations in 5 s, old → new |
| --- | --- | --- | --- |
| 120 BPM | 1.440 → 0.452 ms | 2.717 → 0.799 ms | 2,755 → 537 |
| 180 BPM | 1.449 → 0.272 ms | 2.859 → 0.405 ms | 2,767 → 725 |

A separate three-pass Windows thread-cycle measurement gave 171.2M → 45.6M cycles per five seconds at 120 BPM and 159.1M → 60.2M at 180 BPM. In an empty 48 kHz session with 64-frame buffers, enabling snapshot publication increased the median callback cost from 1.758 to 1.792 µs (four interleaved measurements, 100 callbacks per timed batch). Each active callback uses a nonblocking snapshot write. A busy reader defers publication to the next callback. MIDI I/O and sleeping run on the worker.

## Regression coverage

All four supplied probes failed on the original head. Permanent tests verify receiver pulse position on both sides of sixteenth boundaries, one locate despite a stale UI position or a contended callback publication, recovery after an out-of-range locate, remapping elapsed tempo, wrap and stop inside a buffer, and recovery from a failed MIDI send. The UI test exercises a port name longer than 200 characters with surrounding spaces. Tests also cover ordinary 24 PPQN playback, delayed Start cancellation, and a stalled audio device.

On Windows, `cargo test --locked -p soundcraft-model -p soundcraft-playback -p soundcraft-ui-egui --lib --no-fail-fast` passed 456 tests (1 model, 113 playback, 342 UI). `cargo fmt --all -- --check` passed. In an isolated integration checkout with #1536, all-target Clippy passed for engine, model, playback and UI with `-D warnings`. Standalone workspace CI still depends on the previously identified upstream Windows engine lints.

## Review and merge order

This branch targets upstream main and contains the Beat Clock feature alone. Its MIDI encoding dependency is pinned to a commit already in upstream craft-libs. It is independently reviewable from the MTC feature. Draft pending the Windows workspace gate tracked in #1535 and fixed by #1536. Merge #1536 first, then Beat Clock after the gate passes. Then refresh #1663 to reconcile the shared Player start/stop paths before merging MTC. Keep #1661 open for both deliverables.

