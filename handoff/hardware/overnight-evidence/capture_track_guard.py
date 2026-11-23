from pathlib import Path
import sys
w=Path(sys.argv[1]); p=w/'crates/playback/src/mtc_preroll.rs'; s=p.read_text()
s=s.replace("            || mixer.record_arm\n            || mixer.input_monitor\n            || mixer.input != Route::None\n","")
old="        let Some(playlist) = track.playlist() else { return false };"
new="""        let Some(playlist) = track.playlist() else { return false };
        // A muted, empty recording strip with no inserts, sends or automation
        // cannot contribute to a dry guide. Arming it for metering is common.
        if track.kind == TrackKind::Audio && mixer.mute && playlist.clips.is_empty() {
            continue;
        }
        if mixer.record_arm || mixer.input_monitor || mixer.input != Route::None {
            return false;
        }"""
assert s.count(old)==1
p.write_bytes(s.replace(old,new).encode())
p=w/'crates/playback/src/mtc/tests/silent_preroll.rs';s=p.read_text()
old='        let (mut audio, tx, _) = callback(s, 48000.);'
new="""        // The hardware acceptance routes USB input to an armed, muted meter strip.
        let meter = s.add_track(TrackKind::Audio, ChannelFormat::Mono, None);
        let mixer = &mut s.track_mut(meter).unwrap().mixer;
        mixer.mute = true;
        mixer.record_arm = true;
        let (mut audio, tx, _) = callback(s, 48000.);"""
assert s.count(old)==1
p.write_bytes(s.replace(old,new).encode())

