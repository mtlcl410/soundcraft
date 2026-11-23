## What this PR does

Send Beat Clock, transport and Song Position Pointer to selected MIDI outputs. A stopped locate sends one SPP immediately. After an output timing interruption, repay missing clocks evenly within one quarter note. Each destination has its own ±250 ms calibration. Duplicate port names have numbered destinations; a known device remains bound to its saved endpoint. Warnings require a route using device compensation. A damaged preference resets individually and is identified at startup.

The scheduler uses the `craft-midi-sync` alias at `08da5e14` (MIT OR Apache-2.0) alongside the existing `craft-midi` revision to obtain the sync message API. `thread-priority 3.1.1` (MIT) raises the output worker priority where supported. Both licenses satisfy the project allowlist. Queued MIDI belongs to its originating transport pass. Reconnect retains the selected audio host and port identity.

## Verification

Windows, current head `8fd150681cb7ed2497887fdb784e82e1c399bafa`. The Beat Clock labels and diagnostics fall back to English until translations are supplied by craft-i18n. The pt-BR catalog matches upstream main at this revision. GitHub Actions: CI `action_required`, Nix `action_required`, SonarCloud `action_required`, ast-grep `action_required`.

| Current-head check | Result |
| --- | --- |
| `cargo test --locked -j 2 -p soundcraft-ui-egui --lib -- --test-threads=2 localization::tests:: every_preference_text_has_a_portuguese_translation` | 16 passed |
| `cargo fmt --all -- --check` | Passed |

Earlier full-suite and regression results below were measured on `56169122`.

| Command | Result |
| --- | --- |
| `cargo test --locked -j 2 -p soundcraft-playback --lib -- --test-threads=2` | 170 passed, 1 ignored |
| `cargo test --locked -j 2 -p soundcraft-ui-egui --lib -- --test-threads=2` | 364 passed |
| `cargo test --locked -j 2 -p soundcraft --bin soundcraft -- --test-threads=2` | 56 passed |
| `cargo clippy --locked -j 2 -p soundcraft-playback -p soundcraft-ui-egui --lib --tests --no-deps -- -D warnings` | Passed |
| `cargo fmt --all -- --check` | Passed |

Before the fixes, a superseded locate could still emit its queued SPP, a rejected Stop vanished from the next pass, and a long worker stall exhausted the repayment window without resynchronizing.

[Verification and red/green evidence](https://github.com/storytold/soundcraft/pull/1662#issuecomment-7077795003).

## Hardware status

Earlier Model 12 USB MIDI → DIN → UM-ONE tests verified 20/20 idle starts, 5/5 minimized starts and 20/20 loop-end stops at 480 frames. The −200-sample setting advanced clock arrivals by 4.268/4.071 ms at 120/180 BPM. Physical duplicate-output recovery, 256-frame stop and acoustic alignment remain unverified. Optional loopback: set `SOUNDCRAFT_LOOPBACK_IN` and `SOUNDCRAFT_LOOPBACK_OUT`, then run `cargo test -p soundcraft-playback --lib beat_clock_reaches_a_virtual_midi_receiver -- --ignored --nocapture`. [Hardware evidence](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)

## Known limits

Exclusive audio backends require manual Reconnect. Live plug-in delay changes take effect on the next rendered session revision. Already delivered MIDI retains its timing. Notes/Controllers compensation becomes available when external MIDI track output is supported.

## Open questions

None.

## Merge order

Merge #1662, then #1663, then #1669. #1536 handles independent Windows checks. Part of #1661.
