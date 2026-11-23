### MTC regression results

Verified revision `VERIFIED_HEAD`. The downstream Beat Clock follower was absent from the original-head reproductions.

| Regression | Earlier MTC implementation | Verification |
| --- | --- | --- |
| Five-second timecode duration in a session beginning at 01:00:00:00 | Pre-roll failed with “00:00:05:00 is before the session start” | Pre/post-roll use duration semantics. An absolute Session Setup start label can be moved earlier or later. |
| Full-frame locate at 29.97 non-drop | Source frame 2 mapped to session sample −1 at 48 kHz | The same frame now maps to sample 0, matching Session Setup. |
| Generation at the first integer sample of an even fractional frame | Only the locate was emitted; the first quarter frame was absent | The encoder emits the first QF when starting on the representable boundary, and waits for the next group when starting past it. |
| Edit external offset on a stopped reader | Cursor stayed at 480,000 samples; 528,000 expected | The edit relocates without waiting for another packet. |
| Record queued while enabling Online | Recording refusal left the status empty | Manual Record, transport dispatch and queue servicing explain how to return to recording. |
| Keep Clips at Their Timecode | Automation stayed at 0, 443,072, 2,215,360 and 2,658,432; expected each to move by 86,400,000 samples | Automation follows its edit preference, the rulers retain their data, undo restores both clips and points, and underflow refuses the entire edit. |
| Interleaved MIDI and midnight | F8 interrupted the decoded locate; the 30 fps session moved from 3,974,399,600 to −172,797,200 samples | Full and split messages are covered, along with 30 fps and 29.97 DF forward midnight and adjacent backward locates. A separate test exercises malformed input. |
| Individual preference recovery | 512 Freewheel frames were silently clamped to 40. Invalid workstation sync fields discarded other settings. | Invalid fields are reset with a visible explanation. Valid routes, tracks and unrelated preferences survive. |

Earlier physical measurements used the Model 12, UM-ONE and SD recording. This review increment adds deterministic wire, playback, UI and settings regressions. [Earlier hardware measurements](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268)
