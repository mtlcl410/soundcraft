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

![Per-take MIDI Clock dispatch and recorded crash comparison](IMG/midi-clock-resume-dispatch.png)
