### Beat Clock regression evidence

Windows, tested revision `7ff81296df6d36a565c4636d75da682d52bc5423`. The failures below were observed with the new assertions running against the earlier implementation.

| Scenario | Before | Corrected behaviour |
| --- | --- | --- |
| Move the stopped cursor to sixteenth 7, then repeat | The wire capture contained only `FC` | One `F2 07 00` after the necessary Stop; no F8 or Continue until playback. Repeating the same locate emits nothing. Ordinary stop and loop rollover retain their previous sequences. |
| Unknown output lead with no compensated destination | The unused route reported Unknown | Output timing warnings follow active compensated destinations. The Unknown warning identifies Setup › Playback Engine › Reconnect audio device. |
| Exhaust the three automatic reopen attempts | Eight device enumerations over the next simulated minute | Presence checks are limited to at most two per minute after exhaustion. |
| Poison a render graph lock | The next render returned silence | The output recovery path handles the poisoned guard. |
| Give two outputs the same display name | The second destination was unavailable | Separate calibrations survive reload and enumeration reordering. Removing the first anchored endpoint does not transfer its offset to the other one. Endpoints with indistinguishable native IDs are unavailable. This test used simulated endpoints. |
| Inspect Notes/Controllers compensation | Accessibility exposed the preference as editable | The saved value remains visible in a disabled control. The adjacent explanation describes when it takes effect. |
| Open preferences containing a malformed MIDI value | The whole UI state was rejected | The individual field is reset with a visible message. Other ports, appearance and audio settings survive. |

The 120 BPM / 48 kHz timestamp-gap receiver also checks that all missing F8 messages are repaid evenly within one beat. Previous physical measurements and setup are in the [combined hardware evidence](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268).
