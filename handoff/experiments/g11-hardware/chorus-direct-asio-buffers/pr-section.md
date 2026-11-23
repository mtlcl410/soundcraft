### Direct ASIO buffer sizes on the Model 12

At 44.1 kHz, requesting 128 or 64 frames in SoundCraft while the TASCAM panel was set to 256 still delivered 256-frame callbacks in both directions. Changing the vendor panel and reopening the stream produced the requested sizes. The final run restored and verified 256. Two independent stream opens per setting used the same S-MU2000 project and physical Model 12 → UM-ONE MIDI loop described above.

| Actual frames (in/out) | First Clock to MAIN, mean (range) | Takes with waveform deviations | Low-level windows |
|---|---:|---:|---:|
| 256 / 256 | 27.20 ms (23.59–32.43) | 1/12 | 0 |
| 128 / 128 | 21.52 ms (18.97–26.59) | 2/12 | 1 |
| 64 / 64 | 15.33 ms (12.87–21.14) | 4/12 | 0 |

All 24 starts at 8.000 s produced one crash each. All 12 starts at 8.125 s produced zero, with later accompaniment present in every MAIN recording. The mean includes all eight exact starts per setting. We timestamped the first received Clock and matched the crash on the stereo MAIN USB return, correcting input timestamps by 6.803, 3.900 and 2.449 ms respectively. At 64 frames the mean was 11.86 ms lower than at 256 on this system.

For signal integrity we captured the native 9/10 output and MAIN 11/12 simultaneously. We aligned them once per take, fitted stereo gain, and counted takes with residual steps above 16 counts in 16-bit PCM. A low-level window is 64 consecutive samples with MAIN RMS below 20% of an expected RMS above 30 counts. At both lower sizes the first exact start after reopening showed a discrepancy. The single low-level window at 128 frames lasted 1.45 ms. These are recorded waveform deviations; audibility and their cause remain unverified. No sample clipping or gaps in the callback capture sequence were detected. Injecting a 64-frame mute and a one-sample spike into copies of a clean recording confirmed detector sensitivity. This update adds hardware evidence only.

![Measured MIDI Clock to MAIN latency by actual ASIO callback size](IMAGE_URL)

