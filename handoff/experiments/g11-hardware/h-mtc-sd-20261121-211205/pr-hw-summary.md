**Model 12 SD recording with MTC chase (November 21, build `ee80920`).** On firmware 1.30 0088, the Model 12 recorded CH1 (live mic) and CH2 (S‑MU2000 piano returned over USB) to a 48 kHz / 24-bit SD song. MIDI TIMECODE was on and MIDI CLOCK/SPP was off. The rear DIN output fed the SoundCraft reader via UM‑ONE at 30 fps non-drop, with zero session start and offset, Online enabled, Gen MTC off and Freewheel set to eight frames. All three takes locked, played the backing and followed stop. No transport poll showed SoundCraft recording, an RPC error or a frame-rate mismatch.

| SD take | Start | Recorded | DIN quarter frames | CH2 onset of the scheduled 5.000 s A4 |
|---|---|---:|---:|---:|
| 040208_0004 | Song start | 69.552 s | 8,344 | 5.0135 s (+13.5 ms) |
| 040208_0007 | 2.000 s | 65.680 s | 7,880 | 5.0515 s (+51.5 ms) |
| 040208_0009 | Song start, DIN interrupted during recording | 65.640 s | 7,662 | 5.0555 s (+55.5 ms) |

The onset offset varied by **42.0 ms** across takes using 1 ms RMS windows. Matching the same piano attack independently gave a 41.75 ms spread. The end-to-end measurement does not isolate the source. Both SD tracks were populated in all three takes. The third take’s microphone peaked at −89.08 dBFS, too quiet to verify speech.

During the 1.758 s DIN interruption, the reader reached 8/8 frames and stopped. The first locked-and-playing poll was 311 ms after timecode returned. The SD backing contains the note at 11 s, silence at the expected 12 s attack and the note at 13 s. On replay against the uninterrupted take, the listener heard the pause and no additional click, repeated note or skip on recovery.
