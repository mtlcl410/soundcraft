Unattended scenario results for `0819e610`. The MTC source, output ports, device timestamps and load are simulated. Playback drift is measured against rendered audio; recording was checked in two actual WAV files.

| DJ and concert | Result |
|---|---|
| A-9 / B-2 | 20 rolling relocates generated 20 full frames and 790 quarter frames, maximum reacquisition 190 ms. Thirty eight-bar rewinds generated 30 full frames and 48,000 quarter frames, maximum reacquisition 150 ms at 25 fps. |
| A-10 | At 200 ms of unknown timing the audio matched the reference across 96,000 PCM values. Retained warning at 250 ms, unknown at 300, cleared at 500. No expired packets on recovery: Clock resumed at 500, QF at 540 ms. In the separate 100 ms outage, five expired F8 and ten expired QF deadlines were handed off on recovery, starting 95.833/100 ms late. Red: `scenario_a10_dual_encoder_recovers_after_midroll_invalid_timestamp`. Shared timing and Clock are from #1662; this PR owns the MTC encoder. |
| B-3 | At 25 fps, None and Frames 4/8/40 stopped 80/160/320/1,600 ms after loss. None includes a two-frame loss-detection window. Jam Sync continued 10 s with zero simulated drift at equal rates. Reference: Pro Tools Reference Guide 2026.4, printed p. 1819. |
| B-4 / B-5 | Generator on, chase offline: two WAVs, six attacks, zero sample error, one FF and 200 uninterrupted QF. Online: toolbar, shortcut and queued Record all wrote zero files. Only queued Record omitted the visible reason. Red: `scenario_b5_three_online_record_requests`. |

| Orchestra | Result |
|---|---|
| C-1 / C-8 | Six frame rates × four sample rates for ten minutes. Full-frame locate landed one sample early relative to Session Setup on 67,793 of 390,996 whole-frame comparisons. Example: 23.976 fps/44.1 kHz, frame 1 = 1,839 vs 1,840. Rolling QF error was zero. The identical test on #1669 passed all 390,996; the fix already exists higher in the stack in bfecc6e. Red: `scenario_c1_c8_ten_minutes_six_rates`. |
| C-2 / C-3 | DF minute and tenth-minute transitions were contiguous (1,602 and 1,601 samples at 48 kHz). Across midnight the counter returned to zero and chase remained locked. |
| C-4 | Two hours each at −50/+50 ppm: zero lock losses, zero duplicate/missing beats in the analysed run. Ten documented hard relocates per direction, +1,603/−1,603 samples; peak audible click offsets 33.414/33.373 ms. |
| C-7 | 150 tracks at 48 kHz with 128-sample blocks. Three 1,500-block runs acquired lock and had zero lock losses. For 0/2/6 inserts per track, process CPU was 62.4/101.1/213.8% of one logical core. 175/274/51 blocks exceeded the software 2.667 ms budget on a shared build host. No physical ASIO driver was opened, so these are software deadline misses, not a driver xrun count. |

| Studio | Result |
|---|---|
| D-3 / D-4 | Changing Session Start moved all 13 clips by 86,400,000 samples. Automation, marker and tempo stayed in place with either Automation Follows Edit setting; undo/redo restored exact states. Pre/post-roll expanded 48,000–96,000 to 24,000–108,000. Full frame preceded first QF. |
| D-5 / D-7 | Legacy MTC +100 frames migrated to +160,000 samples. Three of seven malformed session inputs blocked open; four opened without a warning. All source bytes remained unchanged. Red: `scenario_d7_session_reload_recovers_sync_values_and_preserves_score`. The general parser predates this PR; freewheel is owned here. |

| MIDI reader | Result |
|---|---|
| E-1 | F8/FA/FC injected inside a full-frame payload or between F1 and its data: 0/6 MTC messages decoded. Red: `scenario_e1_interleaved_wire_realtime`. A driver that separates real-time messages before delivery can behave differently. |
| E-2 / E-5 | Nine malformed SysEx cases plus missing/reordered/reverse QF sequences did not move transport. Ten million seeded bytes in 1,554,172 payloads, no panic, fixed-size 1,040-byte reader. |

Reproductions remain local for the next review round. No product changes were pushed.
