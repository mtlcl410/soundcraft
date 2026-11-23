### External Clock follow

Windows revision `VERIFIED_HEAD`. These regressions use simulated MIDI timestamps at 48 kHz and compare audio rendered by the SoundCraft mixer against the original sampled voices. A velocity pattern identifies each scored eighth even if an onset is missing or repeated. Offsets below use negative for early and positive for late. The tests print the complete signed series with `--nocapture`.

| Red proof | Reproduction | Correction covered here |
| --- | --- | --- |
| Clock loss under a real brake | The earlier receiver declared loss at 151 ms with the source still running. Across 32 render cases the former path missed 60 attacks and added 40. | Follow the measured growth in pulse spacing. A running source can reach 5 BPM. An explicit Stop, loss of Clock, and return to 128 BPM have separate assertions. |
| Batched 180→60 and 130→80 transitions | Sending each 3–5-pulse batch on its last member's timestamp exposed a dropout in the earlier follower. The old first-member fixture could deliver future pulses. | For each scored attack the test subtracts the positive arrival delay from the measured error, checks the residual, and compares the complete voice. |
| 7.9%, 8.0% and 8.1% | With the old classifier 48/120 trials were wrong. Its transition baseline could include intervals from the new tempo. | Preserve the pre-step estimate and corroborate the candidate against an independent window. The test reports the confirmation pulse for each seeded trial. |
| Short pitch-fader movements | In the earlier PCM a 5% nudge reached 16.375 ms; the staircase and wobble also exceeded their 4 ms targets. | Capture the individual attacks on nudges, linear/convex builds, half/double tempo, staircase and sinusoidal modulation. Check readout settling separately. |
| Invalid cached track or clip | Removing the track caused an index panic. Replacing the clip in the same slot changed its bounds from 24,000 to 48,000 samples. Reverting the acknowledgement guard likewise panicked on an invalid index. | Validate the track slot, clip identity and acknowledgement before mutation. |
| Loop position and release ordering | Restoring local wrap made Continue jump from sample 31,920 into the local loop at 24,128. Resetting an instrument before note release erased its three held keys. | SPP followed by Continue inside or outside a local loop honors external position. External Stop releases pitches 60, 64 and 67 before resetting. |
| Preference migration and accessibility | A malformed field discarded the workstation settings. Reopening a migrated file with 256 input and 256 output calibrations lost the output offsets. The prior transport bar exposed no accessible EXT toggle. | Each damaged field reports its own recovery. Existing two-direction calibrations survive migration. EXT exposes the selected state and the waiting/locked/coasting status. |
| Long-run tempo history | The six-hour A-6 baseline accumulated 2,692 events. | Retain the mapping used by recorded takes and bound unreferenced playback history. Verify the first hour's take after disabling external follow, saving and reopening. |

DETAILED_RESULTS

The hardware evidence uses an actual TASCAM Model 12 and Roland UM-ONE. The DJ matrices and cable-loss simulations described above use the offline renderer. [Model 12 / UM-ONE hardware measurements](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)
