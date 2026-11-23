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

![External MIDI Clock resume latency](IMG/midi-clock-resume-latency.png)

![Crash onset and waveform correlation](IMG/midi-clock-resume-boundary.png)