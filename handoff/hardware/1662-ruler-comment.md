## Model 12 hardware acceptance — measurement chain

At head `8fd15068`, a Windows build with ASIO enabled selected **No audio device (silent)** at 48 kHz with the Model Mixer ASIO driver at 128, 256, and 512 frames. Each run reported `unsupported device sample format I24`. No SoundCraft round-trip measurement is available from these attempts. Packed 24-bit audio support is tracked in #1634.

An independent ASIO player on the same PC did deliver six distinct markers from USB output 1 to USB input 9 on each of 20 stream opens per buffer. Both groups below passed the environment checks. Model 12 firmware 1.50 0103; CH9/10 in PC mode, USB 1/2 routed to CH9/10, MULTI INPUT, OUTPUT DELAY disabled.

| Buffer | Measured round trip (samples) | Driver input + output (samples) | Across-open spread | Within each open |
|---:|---:|---:|---:|---:|
| 128 | 611–616 | 176 + 481 | 5 samples | 0 samples |
| 256 | 987–993 | 304 + 728 | 6 samples | 0 samples |

The predefined repeatability limit was one sample. Both independent groups exceeded it across opens. These are digital USB returns; the measurements do not include the analog MAIN output. The independent 512-frame series was excluded by the environment check. Beat Clock timing and reset acceptance remain pending.
