## What this PR does

Follow an external MIDI Beat Clock for playback and recording. EXT shows Waiting, Locked or Coasting. Coast keeps an open take running and relocks on F8 alone; Stop on loss finishes the take. External position overrides the local loop, rolling SPP is ignored, and Stop releases held notes before resetting instruments. The tempo response is fixed. Invalid follow settings recover field by field with a visible notice. Fixes #1674 and #1675.

Audio and MIDI can record because the beat grid follows the incoming Clock. In MTC Online (#1663), an absolute locate could displace an open take. Pro Tools documents Clock transmission on pp. 743–744; the MPC guide disables audio recording while receiving Clock. The audio/MIDI tests are `coast_keeps_the_audio_and_midi_take_through_clock_loss_and_continue` and `stop_on_clock_loss_commits_the_audio_and_midi_take`. [Pro Tools 2026.4](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf) · [MPC v3.5, p. 60](https://cdn.inmusicbrands.com/Software/SME0-3.5.0/Public/MPC%20Standalone%20OS%20-%20User%20Guide%20-%20v3.5.pdf#page=60) EXT has no default keyboard shortcut. Ctrl/Cmd+J remains assigned to MTC Online. Setup › MIDI › Sync configures the source. Steady fast Clock loss times out at 150 ms, extending up to 1.5 s during slowdown. With Active Sensing the timeout is 300 ms without MIDI activity. MTC chase uses the session External Timecode Offset alone.

## Verification

Windows, current head `33dfa5f5d3b6afd33bf0b6b8df57b755d662a8fa`. The Beat Clock labels and diagnostics fall back to English until translations are supplied by craft-i18n. The pt-BR catalog matches upstream main at this revision. GitHub Actions: CI `action_required`, Nix `action_required`, SonarCloud `action_required`, ast-grep `action_required`.

| Current-head check | Result |
| --- | --- |
| `cargo test --locked -j 2 -p soundcraft-ui-egui --lib -- --test-threads=2 localization::tests:: every_preference_text_has_a_portuguese_translation` | 17 passed |
| `cargo fmt --all -- --check` | Passed |

Earlier full-suite and regression results below were measured on `b68907e6`.

| Command | Result |
| --- | --- |
| `cargo test --locked -j 2 -p soundcraft-mix --lib -- --test-threads=2` | 104 passed |
| `cargo test --locked -j 2 -p soundcraft-playback --lib -- --test-threads=2` | 267 passed, 2 ignored |
| `cargo test --locked -j 2 -p soundcraft-ui-egui --lib -- --test-threads=2` | 439 passed, 6 ignored |
| `cargo test --locked -j 2 -p soundcraft-engine --lib -- --test-threads=2` | 486 passed, 1 failed (#1536) |
| `cargo test --locked -j 2 -p soundcraft --bin soundcraft -- --test-threads=2` | 61 passed |
| `cargo clippy --locked -j 2 -p soundcraft-mix -p soundcraft-playback -p soundcraft-ui-egui --lib --tests --no-deps -- -D warnings` | Passed |
| `cargo fmt --all -- --check` | Passed |

The 20-track mix rendered 31,264 eighths exactly once, with complete waveforms and tails. Among 28,684 steady eighths outside transitions and batches, absolute error p99.9 was 3.479 ms. In the 128 batched eighths the largest **positive residual after MIDI arrival** fell from +846 to +1 sample. The earliest onset against the grid was -15 samples. The 96 single-to-group cases peaked at +209 samples (4.354 ms) of extra delay, with zero missing, repeated or damaged attacks. Across 96 established grouped slowdowns, the maximum absolute residual was 0 samples. The tests rotate group phase for widths 3, 4, 5 and variable groups.

The ±8% ramps peaked at 3.6458 ms and the eight-hour jitter simulation peaked at 130 samples. In the paired six-hour history run, capped/uncapped peak events were 512/5193, peak process working sets 13.8/14.3 MiB, and end-of-run publish p95 14.400/94.000 µs. History required by recorded takes is retained. The EXT UI regression previously observed an empty status after a refused click. It now displays the refusal reason.

Reproduce them in PowerShell:

~~~powershell
@('twenty_full_length_dj_tracks', 'six_hour_clock_history_has_bounded_unreferenced_events', 'six_hour_clock_history_uncapped_control', 'eight_hours_of_clock_flutter', 'ten_minutes_of_coalesced', 'slowdown_device_phase_sweep') | ForEach-Object { cargo test --locked -p soundcraft-ui-egui --lib $_ -- --ignored --nocapture --test-threads=1 }
~~~

[Verification and red/green evidence](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7077834130).

## Hardware status

TASCAM Model 12 → Roland UM-ONE with S-MU2000: one crash from 8.000 s, none from 8.125 s, and all eight snares at 100 and 120 BPM on MAIN. The new DJ profiles use simulated Clock and rendered PCM. Akai MPC hardware remains untested. [Hardware measurements](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)

## Known limits

In this 20-track mix, including batches while still excluding the declared tempo transitions gives 34.292 ms p99.9 against the grid. An event already predicted on the grid may precede its F8; one arrived 1645 samples after the predicted onset. Grouped slowdown delivery alone added up to 166.667 ms. After an abrupt slowdown, audio already delivered to a large device buffer can be late: across 18 configurations, the largest observed positive errors were +86.500 ms at the first offbeat and +83.271 ms at the first beat. For live use, try 64–256 frames where supported. #1686 tracks one unexplained waveform difference in twelve 256-frame takes. A separate 64-frame capture had 40 near-silent samples.

## Open questions

None.

## Merge order

#1662 → #1663 → **#1669**. Part of #1661. [Review just this layer](https://github.com/mtlcl410/soundcraft/compare/feat/g11-mtc-generate-chase...feat/g11-external-clock-follow).
