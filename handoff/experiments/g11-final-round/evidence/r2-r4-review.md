### Grouped MIDI Clock delivery during playback

The production mixer rendered the same deterministic 48 kHz scores on `d2632db4` and with fix `9c3a9c7`. The follower now retains the established song grid while the timing of an arriving batch is ambiguous, discards stale settling estimates when it detects grouped delivery, and lets a confirmed tempo change reach its scheduled join. In these tests, **grid error** is PCM attack time minus the score time. **Wire wait** is the delay of that note's F8 against the score. **Residual** is grid error minus wire wait. Positive residual is additional lateness after the F8 was available.

| Render | Before | With the fix |
|---|---:|---:|
| First grouped eighth, worst additional delay across 96 cases | +113.438 ms | +0.208 ms |
| Later grouped eighths, worst additional delay in those cases | +105.063 ms | +4.354 ms |
| Earliest attack against the score in those cases | −110.792 ms | −0.958 ms |
| Single-to-group transitions, empty / multiply occupied eighth slots | 20 / 20 | 0 / 0 |
| Previously grouped input slowing from 180→60 or 130→80, 96 cases | 4 empty / 4 multiply occupied slots in startup | 0 / 0 throughout. All 1,536 post-change attacks landed at their wire time |
| Twenty-track mix, worst additional lateness on its 128 grouped eighths | +17.625 ms | +0.021 ms |
| Twenty-track mix, earliest grouped attack against the score | −0.313 ms | −0.313 ms |

The single-to-group matrix covers 120 and 148 BPM, ideal input and seeded ±1 ms jitter, and all cyclic offsets for fixed widths 3, 4 and 5 and variable widths 3/4/5. All 1,552 post-switch eighths had a single complete attack. The slowdown matrix covers both a bar line and a mid-beat cut. Its phase check visits every possible distance from the **same first offbeat** to the tail of its group, for each grouping pattern. The maximum physical wait in those slowdowns was 166.667 ms. Both matrices checked complete note waveforms and tails.

| Eighth in the 20-track mix | Wire wait (samples) | Old grid error | Fixed grid error | Old residual | Fixed residual |
|---:|---:|---:|---:|---:|---:|
| 7584 | 1,630 | −15 | −15 | −1,645 | −1,645 |
| 7585 | 1,663 | +2,509 | +1,662 | +846 | −1 |
| 7586 | 1,626 | +2,268 | +1,627 | +642 | +1 |
| 7587 | 1,623 | +1,998 | +1,623 | +375 | 0 |
| 7588 | 1,665 | +1,741 | +1,665 | +76 | 0 |
| 7589 | 1,580 | +1,580 | +1,580 | 0 | 0 |

The first attack (#7584) was already on the previously locked grid when the sender started holding packets. It preceded its F8 by 34.271 ms, and preceded its intended score time by 0.313 ms. Later attacks include the actual wire wait. All 31,264 attacks and tails were accounted for. Score-error p99.9 was 3.479 ms for 28,684 ordinary eighths outside transitions and 34.292 ms when grouped delivery was included in that comparison.

The device-lead comparison also rendered 58,752 note/click attacks with zero empty or multiple slots and zero damaged waveforms. With a simulated 2,048-sample output buffer, a 50 ms deadline and a 300→240 BPM drop, the worst predictive result was +86.500 ms on the first offbeat and +83.271 ms on the first beat. These are separate maxima over callback and pulse offsets. These timing results use software-rendered PCM and simulated input delivery.

To reproduce the individual signed observations in PowerShell:

```powershell
$env:SOUNDCRAFT_PACKET_TRACE = '1'
cargo test -p soundcraft-ui-egui --lib first_usb_batches_mid_song_render_at_their_wire_time -- --nocapture
cargo test -p soundcraft-ui-egui --lib trailing_packed_slowdowns_preserve_every_attack_at_its_wire_time -- --nocapture
cargo test -p soundcraft-ui-egui --lib twenty_full_length_dj_tracks_preserve_the_recorded_eighths_through_transitions -- --ignored --nocapture
```

For the old result, apply only the changes to the two test files from `9c3a9c7` on top of `d2632db4` and run the same commands. All three tests fail there.
