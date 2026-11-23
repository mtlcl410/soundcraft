# External MIDI Beat Clock response

These are 48 kHz software-rendering measurements for external MIDI Clock follow. The input is a deterministic sequence of timestamped F8 messages. The measurements use actual sampler attacks, releases and metronome PCM. A positive error means the attack was late relative to the source score. Device buffering is simulated in these tests.

## Abrupt tempo changes

Each case has eight post-change beats of eighth notes. Pulse 384 is a bar line and pulse 396 is halfway through a beat. Each cell gives the signed deviation of the first eighth after the cut (ms), maximum absolute deviation from the second beat onward (ms), and number of received F8s until confirmation. The packed input cycles through groups of three, four and five pulses within 1 ms with gaps between groups. A batch is timestamped at its first pulse.

{{PACKETS}}

Across the 36 cases all 1,782 expected notes had a single attack and the complete 96-sample voice. At ±1 and ±2 ms, the two-interval path confirmed 8 of 12 changes in each profile. The four-interval path handled the remaining four at the third or fourth incoming F8 after the cut (an interval can span the cut). Under grouped delivery, two or four independent group intervals took seven or fifteen received F8s. Each changed train produced one confirmation. No confirmation preceded the change. The 10/4 ms ideal-input thresholds remain a separate regression. With timestamp jitter three later peaks exceeded 4 ms. The jitter regression enforces 10 ms on the first eighth and 6 ms thereafter; the ideal-wire regression still enforces 10/4 ms. The most extreme packed slowdown was 196.896 ms early.

Four additional ten-minute, 120 BPM runs used group widths of 3, 4, 5 and cycling 3–5. Each rendered 2,400 intact eighth notes with zero false steps, dropouts or onset error. The prior head produced 194 loss indications and 88 empty/88 overfull eighth-note slots across the twelve variable-burst changes. Shifted onsets can leave a slot empty even when the raw attack count is unchanged.

## Output deadlines

A locked follower may project as far as the end of the audio the device actually requests. A callback shorter than one F8, missing presentation timing, an overdue pulse, a detected rate change or non-uniform packet delivery uses the existing wire limit. A later transition into Coast follows the configured loss policy. The sampler and click continue to render their tails at the device rate.

Each steady range covers individual note and click attacks. Hard uses the last received F8 plus one pulse. Selected allows bounded prediction. For the slowdown, the source rate drops by 20% (200→160, 240→192, 300→240). Each row sweeps all 24 pulse positions in the beat and four callback alignments. Offbeat is the first subsequent offbeat and Beat is the next quarter-note boundary strictly after the cut. Values are worst signed errors by magnitude in ms across the 96 alignments. If the change lands exactly on a quarter-note boundary, the attack on that boundary spans +20.646…+82.875 ms with the hard cap and 0…+57.979 ms with the selected policy. The reference includes presentation lead, so adding driver latency again would double-count it.

{{DEVICE}}

{{DEVICE_RESULT}}

Once PCM is committed to the device, a tempo change cannot revise it. An early attack in the device queue and a late attack held by the strict wire limit have different causes. The measured maxima describe these settings and phases. Other drivers, block alignment and clock sources can give different results.

## Continuous tempo and stability

The 124 BPM round trip took 32 bars out and 32 bars back for each ±8% excursion. First-pulse estimation was excluded from the BPM display statistic. The regression requires the transport to be locked and one beat of estimates to have arrived. The linear period/phase fit continues to reject jitter. When the long fit detects sustained curvature above the residual noise floor, the writable tempo grid makes smaller, more frequent corrections.

| Source excursion | Clean | ±1 ms | ±2 ms |
| --- | ---: | ---: | ---: |
| +8% and return | 2.3542 | 2.4375 | 3.8333 |
| −8% and return | 2.7708 | 2.9167 | 3.7500 |
| 124.0→124.3→124.0 BPM | 3.1042 | 3.0625 | 3.7917 |

Values are peak absolute PCM onset error in ms. The six ±8% runs each rendered 513 complete notes. The three smaller drift runs each rendered 257 complete notes with zero continuous-ramp or abrupt-step detections. The previous worst was −435 samples (−9.0625 ms). The maximum post-acquisition change between consecutive BPM estimates was 0.09139 BPM.

The existing eight-hour flutter simulation retained its 148-sample grid peak. A separate chronological eight-hour sampler render had identical before/after records for all 115,201 attacks, peak 234 samples (4.875 ms), zero false steps and every 96-sample voice intact. The nine steady BPM and phase p95 pairs were unchanged. The 12 ideal abrupt changes, the 128↔140 BPM controls and Coast relock are checked separately.

## Reproduction

Run each command from the workspace root. The packet trace option emits signed sample errors for every eighth and the pulse positions at which the detector confirmed a step.

```sh
cargo test -p soundcraft-playback --lib clock_follow::render_lead -- --nocapture
cargo test -p soundcraft-ui-egui --lib packet_steps -- --include-ignored --nocapture
cargo test -p soundcraft-ui-egui --lib slowdown_device_phase_sweep -- --ignored --nocapture
cargo test -p soundcraft-ui-egui --lib ramp_response -- --nocapture
cargo test -p soundcraft-ui-egui --lib large_steps -- --nocapture
cargo test -p soundcraft-ui-egui --lib returning_clock_without -- --nocapture
cargo test -p soundcraft-ui-egui --lib eight_hours_of_clock_flutter -- --ignored --nocapture
```

Set `SOUNDCRAFT_PACKET_TRACE=1` before the packet run for the individual attacks. Set `SOUNDCRAFT_SWEEP_DIR` to a directory to export both per-attack slowdown matrices. The acceptance thresholds are SoundCraft targets. Avid describes Beat Clock output and measuring fixed offsets in the [Pro Tools Reference Guide 2026.4, printed pp. 743–744](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf#page=845). Bitwig offers a synchronization response control that trades rapid tracking for smoothing of unsteady clocks. [Bitwig Studio User Guide, Dashboard › Synchronization Settings](https://www.bitwig.com/userguide/latest/the_dashboard/)
