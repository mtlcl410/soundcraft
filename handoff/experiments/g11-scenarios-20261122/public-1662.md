Unattended G-11 scenario results for `91366d09`. These local tests exercised the production MIDI worker and mixer against simulated ports. Audible timing was measured from PCM. Thresholds below are acceptance proposals unless a protocol rule is named.

| DJ | Result |
|---|---|
| A-7 | −250/0/+250 ms across four rates. Worst handoff error 0.494 ms. Out-of-range requests capped at ±12,000 samples at 48 kHz. |
| A-8 | A failed on its eighth clock. B continued with 63 clocks. A reported unavailable and reconnected at SPP 10, then Continue and Clock. First actual Clock handoff +0.572 ms, minimum following spacing 20.506 ms. |
| A-10, integrated on #1663 | A 100 ms unknown-timestamp interval emitted no clocks while timing was unknown. At recovery five already-due F8 packets were delivered; the first was 95.833 ms late. At 200 ms there were no expired packets on return. Confirmed independently on this exact #1662 head by red test `a10_first_clock_after_unknown_lead_is_handed_off_on_time`: expired pulses were handed off at 200/201/202/203/204 ms. Local red test on the integrated tree: `scenario_a10_dual_encoder_recovers_after_midroll_invalid_timestamp`. The timing worker/Clock cursor first appears here. |

| Concert | Result |
|---|---|
| B-1 | 4,608 pulses per set-list run. At 48 kHz max interval error 0.1042 ms. Correct SPP at all 11 nonzero starts; no SPP for the same 11 stopped locates. Local red test: `b1_stopped_setlist_locates_send_marker_spp`. |
| B-7 | Two hours at each of 44.1/48/96/192 kHz with 2,048 samples of mixer PDC. Compared 14,401 rendered attacks per rate to actual Clock writes. Max errors 0.499/0.333/0.167/0.333 ms. |
| B-8 | Without any sync destination, a 10 ms callback simulation showed retained lead at 20 ms, unknown at 40 ms, clear at 60 ms. For an injected 20 ms callback outage the waveform gap was exactly 960 samples at 48 kHz. Actual driver reopen time remains unmeasured. |

| Orchestra | Result |
|---|---|
| C-5 | 24,000 pulses at each rate, 1,000 tempo changes, four meters. Worst handoff error 0.1248 ms, all 1,000 nonzero locate positions correct. Median time per 1,000 locates at 48 kHz was 0.8344 ms on a dense map and 0.4977 ms on a flat map. |
| C-6 / C-8 | 24 tempo/rate combinations, 96 pulses each; worst handoff error 0.1198 ms. Stored 4,800 samples correspond to 108.844/100/50/25 ms across the four rates, as documented. |

| Studio | Result |
|---|---|
| D-4 | Starting from pre-roll beat 6 sent SPP 24, Continue, Clock. The host honoured the extended selection up to post-roll. |
| D-5 | Reopen preserved −2,501 samples. Two destinations with the same name shared one key; setting +701 then +302 retained only +302. Missing original name was reported. Local red test: `d5_station_calibration_rename_and_same_named_units`. |
| D-7 | On #1669, corrupting a type in any of four #1662 boolean preferences rejected the entire settings file. Two extreme integer offsets opened without a diagnostic. The existing desktop loader also uses whole-file fallback on main; original bytes were unchanged in the probe. Local red test: `scenario_d7_corrupt_sync_settings_recover_independently_with_diagnostics`. |

Test sources are kept locally for the next review round. The PR head and draft status are unchanged.
