Unattended Clock-follow performance and studio tests on `6b82d9bc`. Each musical timing result below is measured from a rendered instrument attack against the independent master grid. Hardware round-trip latency is outside these figures.

| DJ | Result |
|---|---|
| Additional continuous 80 → 130 → 80 BPM song | Eight bars per section. All 192 hi-hats, 48 kicks and 48 snares were present. The last hit retained all 96 samples; zero extra attacks in the following second. Hi-hat peak error at the changes was 17.896 ms and 70.104 ms. Final hi-hat/kick/snare were +4.750/+5.875/+5.521 ms. Red against the proposed timing target: `scenario_edm_eighty_one_thirty_eighty_rendered`. |
| A-1 / A-2 | A small 124→124.3→124 ramp stayed within 3.792 ms. ±8% sweeps peaked at 9.062 ms; zero false tempo steps. BPM readout changed ≤0.091 after the first beat. Red: `scenario_a1_pitch_fader_rendered_hats`. For 128↔140 steps, all 16 direction/phase/sample-rate cases passed: first eighth −4.312 to +3.492 ms, later ≤0.750 ms. |
| A-3 | A deck stalled for 300 ms, then sent a new tempo and phase with F8 alone. Coast still displayed Coasting; 65/65 attacks arrived, the last +473.438 ms. Stop remained stopped. Red: `scenario_a3_resume_pulses_without_start`. |
| A-4 / A-5 | Three 10-minute runs bunching 3/4/5 pulses, zero loss or false tempo steps after acquisition. Fifty random Starts and fifty Continues all landed correctly. All 100 notes released; 58 via explicit note-off and 42 via the existing plugin reset on Stop. Red only for the proposed one-for-one event policy: `scenario_a5_notes_released_across_random_stops`. The reset policy is shared with main. |
| A-6 | Six simulated hours, 1,168,942 pulses and 63 tempo changes. Hour-end PCM error −1.667 to +2.562 ms. At most two pending actions observed. Retained tempo history grew from 529 to 2,703 events (43,248 live payload bytes); no fixed history bound or audio-thread allocation guarantee established. |

| Concert, orchestra and studio | Result |
|---|---|
| B-6 / D-1 | Record audio and MIDI, disable follow, save/reopen and render each stem independently. At 100→120 BPM all six paired attacks differed by zero samples. Reopen/split/heal/copy/paste/consolidate/loop also preserved zero-sample alignment, up to 24 paired attacks. |
| C-8 / D-6 | All four audio rates passed the A-2 step render. At 48 kHz, input offsets −12,000/0/+12,000 produced audio/MIDI take starts 108,000/96,000/84,000 samples. Six attacks per stem shifted together. |
| D-2 / D-5 / D-7 | A local loop stayed enabled but had no active playback range when Continue followed an inside/outside SPP. Legacy input offset migrated with inverted sign. Wrong types in each of three follow preference fields caused the desktop loader to reject the settings file. Local red: `scenario_d7_corrupt_sync_settings_recover_independently_with_diagnostics`. The whole-file fallback also exists on main. |

| MIDI reader | Result |
|---|---|
| E-1 / E-3 | The Clock reader decoded interleaved real-time bytes. Invalid SPP data was discarded. Two successive SPPs resolved in order; Continue used the last one. SPP during play was ignored. MTC-specific decoding evidence is on #1663. |
| E-4 / E-5 | At 1 pulse/10 s the status was Coasting; at 10,000 pulses/s Locked, neither had usable BPM. Ten million seeded bytes, no panic, fixed 4,608-byte reader, highest observed queue occupancy 6/32. |

The head and draft status are unchanged. Failing cases remain local pending the separate fix/review round.
