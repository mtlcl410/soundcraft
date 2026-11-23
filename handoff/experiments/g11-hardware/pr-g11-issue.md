## Goal

Give musicians two ways to synchronize a SoundCraft session with external MIDI gear. A sequencer or drum machine should follow the session tempo and transport. A timecode device should be able to follow SoundCraft, or lead it when SoundCraft is online.

## Acceptance

- [ ] MIDI Beat Clock output. Select a named output and signed sample offset. Verify 24 clocks per quarter note, Start and Stop from the beginning, and Song Position Pointer followed by Continue on a nonzero start.
- [ ] MIDI Time Code generation and chase. Generate full-frame locates while stopped and quarter-frame messages while rolling. Cover 24, 25, 29.97 drop-frame and 30 fps, including the first and tenth minute boundaries. Select a chase input and verify located playback, continuous follow and stop.
- [ ] For chase playback, verify that the instrument plays the note on the locate point, preserves the opening half-second interval and stays within 10 ms of the external source at the 17-second checkpoint. Compare short-window pitch against local playback during acquisition.

I am preparing separate Beat Clock and MTC pull requests. Their descriptions will include the Windows hardware routing, packet and audio observations, automated regressions, and merge prerequisites. LTC, word clock, video reference and Satellite linking remain separate G-11 work.
## Linked implementation PRs

1. #1662 implements and tests MIDI Beat Clock output.
2. #1663 implements and tests MTC generation and chase.

Both target main and are available for independent review. For landing, merge #1536 (Windows workspace verification), then #1662, then refresh and merge #1663. The two features share the playback transport start/stop implementation. Keep this issue open until both are merged.
