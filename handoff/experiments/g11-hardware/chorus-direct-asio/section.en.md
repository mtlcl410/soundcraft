### Direct hardware playback from the external Clock

SoundCraft sent the same 48 kHz eight-bar S-MU2000 project directly through Model Mixer ASIO to physical outputs 9/10 (44.1 kHz, 256 frames). The local Windows build combined the Clock follower at `2b53c7e` with the Model 12 sample-format support in #1634 and hardware routing at #1635 (`7e922669`). These routing prerequisites apply to this hardware test. The original project was copied byte-for-byte and its stereo output was mapped to channels 9/10 in memory.

| First Clock at UM-ONE to crash onset on MAIN USB 11/12 | Mean (range), four 8.000 s starts |
|---|---:|
| Previous 20 ms monitor prefill | 62.49 ms (57.47–65.47) |
| Direct SoundCraft ASIO output | **28.07 ms (24.21–32.03)** |

The direct takes measured 32.03, 27.57, 28.45, 24.21 ms. Direct playback averaged **34.42 ms faster** on this setup. Both runs used the same 120 BPM physical MIDI path (Model 12 DIN OUT to UM-ONE), four exact starts, two 8.125 s starts, the same waveform threshold (0.90), and the same driver input-time adjustment (6.80 ms). The previous run recorded through the external monitor process. The driver rejected a second independent ASIO client during direct playback, so a local input-only diagnostic copied MAIN 11/12 samples from SoundCraft’s native duplex stream to a background writer. The diagnostic did not forward audio or alter playback scheduling. Results describe the recorded MAIN return across separate runs.

Direct MAIN contained exactly one crash in **4/4** exact starts and zero in **2/2** late starts. Later accompaniment was present in all six (minimum correlation 0.994). Each take captured its specified Song Position, Continue, 144 Clock pulses and Stop. The input-block sequence was continuous in every take.

![Direct ASIO and 20 ms monitor route measured on the same chorus](IMAGE_URL)