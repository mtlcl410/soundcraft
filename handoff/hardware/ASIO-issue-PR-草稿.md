# ASIO recovery · GitHub drafts

## Issue

**Title** — Windows ASIO: audio callbacks stay at ~251 ms after leaving USB storage mode

On a TASCAM Model 12 at 48 kHz with a 256-sample ASIO buffer, callbacks normally arrive every 5.33 ms. After leaving USB storage mode, the existing stream can stay open and deliver only about four callbacks per second. SoundCraft continues to see the stream as active and leaves audio unusable until the stream is reopened.

### Reproduce

1. Open the Model 12 for ASIO input and output at 48 kHz / 256 samples. Use an idle SD card and keep the hardware recorder stopped.
2. Enter USB STORAGE, safely eject the SD volume in Windows, and return to the song screen.
3. Observe native ASIO buffer switches on the stream that was already open. In three runs on upstream main with #1634 added for packed I24, the median intervals after STORAGE were 250.94, 251.09 and 251.08 ms. An independent ASIO player reproduced the slowdown. Reopening its duplex stream in the same process restored normal cadence.

**Expected:** When playback and recording are stopped, SoundCraft should recover the selected audio route automatically. Active playback and recording should finish or be stopped by the user before the stream is rebuilt.

**Tested on:** Windows 11, TASCAM Windows Driver 2.20, Model 12 firmware 1.50 0103. Both the independent player and the SoundCraft control build reproduce the slow cadence without the MIDI sync feature branches. The underlying driver/device cause remains undetermined.

## Pull request · base main · ready for review

**Title** — Windows: recover persistently slow ASIO streams when transport is idle

SoundCraft restores audio automatically when a Windows ASIO stream keeps calling back far below the configured rate.

Fixes #<issue number>.

The existing watchdog sees a progressing callback counter even when a 256-sample stream at 48 kHz takes ~251 ms per callback. This change detects four consecutive intervals of at least 100 ms and at least eight nominal buffer periods. Once playback and recording are stopped and no transport change is pending, SoundCraft reopens the original device with the same routing, format, sample rate and buffer size.

### Verification

| Check | Result |
|---|---|
| Regression on the previous implementation | `sustained_slow_asio_callbacks_request_idle_recovery` failed with the recorded slow intervals. On the standalone fix, the Windows ASIO playback library suite passed all 108 tests. |
| Model 12, real USB STORAGE, three cycles | While SoundCraft was playing, the first two streams remained open at 250.97 and 250.95 ms. Both recovered after Stop. The third recovered while already stopped. All three recovered playback windows averaged 5.33 ms, with 1,499/1,499 intervals in 4–7 ms per window and continuous sample positions and callback sequence numbers. No manual Reconnect was used. |
| Audio after recovery | The same A4 matched both the output and USB return in all three cycles (correlation >0.99999). The largest change in round-trip timing from baseline was 0.063 ms. |
| Active recording | A separate fault-injection test kept the recording running and deferred the rebuild until recording stopped. |

The fix targets main and has no G-11 dependency. The Model 12 hardware build also included #1634 to open its packed 24-bit format. That change is separate from ASIO recovery. Verification above is local on Windows.
