# G-11 Beat Clock output scenario results

Owning PR [#1662](https://github.com/storytold/soundcraft/pull/1662), tested commit `91366d09fd5f925492152c00be914d7dff7c0330`. The harness adds local Rust tests to the PR checkout. It uses the production encoder, routing worker, timing publisher, mixer, per-port settings commands and settings serialization. The MIDI capture endpoints and driver timestamps are simulated. B-7 measures impulses from rendered PCM. MIDI dispatch timestamps in the other output-only scenarios are protocol measurements.

## A. DJ

| Test | Result | Evidence |
|---|---|---|
| A-7 | Pass at all four rates | At 128 → 140 BPM, three ports at −250/0/+250 ms delivered 522/508/494 pulses over the same 10-second wall-time capture. Maximum send-time error at 44.1/48/96/192 kHz was 0.494/0.458/0.468/0.468 ms, the same for all three ports. Maximum tagged target error was below 1 µs. Out-of-range requests capped at ±250 ms at each rate. Counts differ because offset changes which edge events are inside the capture. |
| A-8 | Pass, simulated disconnection | The production worker reported “A: device gone” after the eighth Clock attempted on A. B continued with 63 Clock messages across the run. A resumed at SPP 10, Continue, Clock. The first Clock was tagged exactly at the SPP grid; actual first sink write was 0.572 ms later. The minimum observed Clock spacing was 20.506 ms (20.833 ms tagged). The companion UI status-line regression passed. Timing of the physical USB driver is outside this run. |
| A-10 | Proposed 1 ms recovery target missed on #1662 | At 48 kHz, 120 BPM, with valid callback lead until 100 ms, unknown for 100 ms, then valid at 200 ms, the compensated Beat Clock destination sent zero F8s while timing was unknown. The first recovered F8 was due at 104.166667 ms and actually handed to the virtual output at 200.000000 ms, **95.833333 ms late**. Five stale F8s due at 104.167/125.000/145.833/166.667/187.500 ms were handed off at 200–204 ms, one per millisecond. The next current-grid F8 was due at 208.333 ms and handed off at 209 ms. Local red test: `a10_first_clock_after_unknown_lead_is_handed_off_on_time` on #1662. The integrated #1663 dual-encoder test shows the same Clock result; #1662 alone reproduces it. |

## B. Concert

| Test | Result | Evidence |
|---|---|---|
| B-1 | Open question, stopped locates | At each of four session rates, 4,608 pulses followed 12 four-bar songs with a two-bar ritardando expressed as one tempo event per beat. Across the four rates, the maximum interval error was 0.1211 ms. Re-entering play at 11 nonzero song positions emitted 11 correct SPPs. Jumping to the same positions while stopped emitted 0/11. Red test on #1662 is `b1_stopped_setlist_locates_send_marker_spp`. The 16th-note SPP units are defined by the protocol. The requested send-on-every-stopped-locate behaviour is a proposed workflow. |
| B-7 | Pass at all four session rates | Four independent two-hour renders with 2,048 samples of actual mixer PDC. Compared the PCM peak on every beat with every 24th simulated sink write. At each rate 14,400 beats plus the terminal check yielded 14,401 matches. Worst errors at 44.1/48/96/192 kHz were respectively 22/16/16/64 samples, or 0.499/0.333/0.167/0.333 ms. Wall time for all four renders was 132.43 s. |
| B-8 | See software recovery boundary below | On simulated 10 ms callbacks, a 12 ms device lead was reported at 0/10 ms, retained with a warning at 20/30 ms, unknown with a warning at 40/50 ms when the new stream had never seen a valid report, and recovered at 60 ms. No sync destinations were configured. |

With working callbacks, direct MixEngine capture contained zero near-silent samples in 3,360 frames (0 ms). A second rendering path skipped exactly two 480-frame driver callbacks on a fixed wall-time grid. The only PCM differences were samples 1,440–2,399 inclusive, or 20.00 ms at 48 kHz. Additional observed gap was 0 samples. The 20 ms is the injected driver reopening interval. The test does not derive an OS reopen time from that number.

B-8 deliberately separates invalid timestamps with a live callback from actual OS device disappearance. The warning bar calls the same `output_timing_issue` shown above even without MIDI configured. A healthy callback can recover spontaneously during playback. `stream_recovery::Retry::decide` defers a WASAPI replacement while the transport is unsafe and `Route::hand_over` requires a stopped transport plus eight recent fresh reports. A synthetic stream reset cannot establish a physical reopen duration, latency or USB dropout.

## C. Orchestra

| Test | Result | Evidence |
|---|---|---|
| C-5 | Pass for output timing | At each of four rates, 24,000 clocks crossed 1,000 per-beat tempo events plus four meters. Worst dispatch error was 0.1248 ms. Every one of 1,000 pseudo-random nonzero sixteenth-note positions produced the correct SPP. At 48 kHz the median of seven trials was 1.3353 ms/1,000 locates on the dense map versus 0.9925 ms on the flat map. An earlier run measured 0.8344 ms and 0.4977 ms respectively. The map costs measurable time. No comparative performance threshold is specified. |
| C-6 | Pass | At 44.1/48/96/192 kHz and 5/20/30/300/999/1,000 BPM, each requested train of 96 pulses was delivered. Max dispatch error across the matrix was 0.1198 ms. |
| C-8 | Per-port storage documented | A saved offset of 4,800 samples produced 108.844, 100.000, 50.000 and 25.000 ms across the four session rates. `docs/midi-input.md` describes preserving the sample value and recapping its effective value at the session rate. |

## D. Studio

| Test | Result | Evidence |
|---|---|---|
| D-4 | Beat Clock pre-roll portion passes | The actual SoundApp play-from-selection entry point expanded samples 192,000–288,000 to 144,000–312,000. At pre-roll beat 6, captured SPP 24, Continue, Clock (F2 18 00, FB, F8). See #1663 for the full-frame/quarter-frame generator half. |
| D-5 | Open question, same-name units | Saving/reopening the workstation MIDI settings kept Deck at −2,501 samples. Renaming to Deck 2 leaves the original calibration on the old name and permits a distinct +900-sample value. Two physical endpoints enumerating under one name share one stored key. Applying +701 then +302 leaves only +302. When only Deck 2 was present, the actual worker attempted only Deck and surfaced “MIDI output Deck unavailable”. The OS-opening path chooses the first duplicate and raises a warning (source inspection). Local #1662 red test is `d5_station_calibration_rename_and_same_named_units`. #1662 implements Beat Clock output. The specified legacy positive-advance input calibration belongs to #1669. Its regression passed: +480 → −480, with an independent −200 output value, preserved on reopening (d5-follow-legacy.log). |

## Reproduction

In checkout `E:/soundcraft/compatibility-audit/g11-beat-clock`, use the adjacent `beat-build.cmd` wrapper for the installed Windows Rust toolchain and SDK. The Cargo arguments are portable.

~~~text
cargo test -p soundcraft-playback --lib scenario_1662 -- --nocapture --test-threads=1
cargo test -p soundcraft-playback --lib a10_first_clock_after_unknown_lead_is_handed_off_on_time -- --nocapture
cargo test -p soundcraft-playback --lib b7_two_hour_pdc_render -- --ignored --nocapture
cargo test -p soundcraft-ui-egui --lib scenario_settings -- --nocapture --test-threads=1
~~~

Final runs: playback scenarios 10 passed, with B-1 and the separately run A-10 recovery test red; the separate long test passed; UI scenarios one passed and one red D-5; five stream-recovery policy tests and the separate UI status-line test passed. Results are in beat-final.log, beat-a10.log, beat-settings-final.log, beat-long-all-rates.log, beat-recovery.log, beat-status-line.log and d5-follow-legacy.log. No product code changed.
