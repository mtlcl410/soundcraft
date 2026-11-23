The Model 12 recorder sent 30 fps MTC over DIN to the UM-ONE while SoundCraft chased Online. This Windows run used firmware 1.50 0103, 48 kHz, a 256-sample ASIO buffer and USB return 1/2 routed to CH9/10. The local build was `f561a57a` (#1669 `33dfa5f5`, including #1663 `bab99312`, with #1634 `a89e9a4e` for packed I24 ASIO). These measurements apply to that combination.

| Recorder start | Rolling MTC (s) | Quarter-frames received | First marker in song (s) | Output 1 offset (ms) | Input 9 offset (ms) |
|---|---:|---:|---:|---:|---:|
| 0:00 | 70.856 | 8,504 | 0.25 | +195.780 | +215.732 |
| 0:00 | 70.589 | 8,472 | 0.25 | +196.727 | +216.548 |
| 0:30 | 70.922 | 8,512 | 30.25 | +196.701 | +217.523 |

Offsets use the received DIN quarter-frame labels as the time reference. First-marker spread on input 9 was **1.791 ms** (target ≤3 ms). Absolute startup delay remained visible. In all three takes the marker **1.25 s after the start position** was missing from both the actual ASIO output and the mixer return. The two neighbouring markers matched their templates. Each take recorded one additional hard relocation near the missing marker. The marker lies wholly inside the interval skipped to rejoin the master.

For the separate recorder reference, SD CH9, ASIO output 1 and USB input 9 shared all **609** unique markers over 608 seconds. Every SD-to-output marker distance was constant to the sample. The input-return interval changed by 36 samples (0.75 ms) in five discrete steps. Both WAVs copied from SD matched their original SHA-256. The MTC and recorder-reference runs passed the environment checks.

**Independent MTC generator over physical DIN**

Each direction used ten takes per rate, alternating start at zero and a nonzero locate. The receiving WinMM interface captured every generated full-frame and quarter-frame message byte for byte. All 200 stopped locates landed on the requested sample. All ten runs passed the environment checks.

| Session fps | UM-ONE → Model 12 onset spread (ms) | Model 12 → UM-ONE onset spread (ms) |
|---|---:|---:|
| 24 | 3.293 | 4.952 |
| 25 | 4.302 | 3.974 |
| 29.97df | 4.285 | 4.126 |
| 29.97nd | 5.857 | 4.839 |
| 30 | 5.015 | 5.105 |

The target was ≤3 ms. None of the ten groups met it. Subtracting a constant audio loop delay and accounting for the direction-specific MIDI path time do not change the spread. The 29.97 non-drop case uses the actual 30000/1001 cadence with non-drop labels.

**Offline replay of the accepted MTC chase rule**

Replaying 301 recorded quarter frames and 478 callback times on #1663 alone (`bab99312`) reproduced the missing attack without Model 12 hardware, an ASIO driver or #1634. Four PCM markers were scheduled at 0.25, 0.75, 1.25 and 1.75 s. The callback rendered three attacks and recorded one hard relocation. The assertion expected four and exited 101. The existing design protects the stopped locate at startup, then seeks forward after one second of sustained phase error. The skipped interval can contain music even with a continuously running master.

The preceding firmware was 1.30 0088. This run used 1.50 0103 and a different audio path and stimulus. There is no firmware-only timing comparison. [TASCAM firmware release notes](https://cf.tascam.com/wp-content/uploads/downloads/products/tascam/model_12/e_model12_rn_vl.txt)

The four-attack assertion represented a superseded expectation. A short sound entirely within the skipped span is correctly omitted. All three hardware rolls preceded STORAGE. Across their 39,824 callback intervals the maximum was 6.499 ms, ruling out the later sustained 251 ms cadence as their trigger. The source of the initial phase difference has not been apportioned. Performance assessment is paused.

**Known limitation.** SoundCraft restores controller state on a seek. It does not re-trigger a sustained MIDI note whose note-on precedes the landing point. Pro Tools documents per-track Note Chasing in the [2026.4 Reference Guide, p. 1043](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf#page=1145).
