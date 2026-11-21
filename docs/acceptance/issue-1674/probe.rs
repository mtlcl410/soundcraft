#[cfg(test)]
#[test]
fn issue_1674_compare_supported_starts() {
    use soundcraft_midi::{Note, Sequence};
    use soundcraft_model::{ChannelFormat, Clip, Insert, TrackKind};
    use soundcraft_playback::midi::MidiInputs;
    use std::time::{Duration, Instant};

    let clock_supported = std::env::var("EXPECT_CLOCK").unwrap() == "1";
    let mut discrepancies = Vec::new();
    for clock in [false, true] {
        for spp in [60u8, 64, 65] {
            let mut engine = Engine::default();
            let s = engine.session_mut();
            assert_eq!(s.sample_rate.hz(), 48_000);
            s.tempo.set_tempo(0, 120.).unwrap();
            let track = s.add_track(TrackKind::Instrument, ChannelFormat::Stereo, None);
            let mut seq = Sequence::default();
            for (start, pitch) in [(15_360, 49), (16_320, 67)] {
                seq.notes.push(Note { start, pitch, length: 120, velocity: 100, channel: 0, release_velocity: 64 });
            }
            let id = s.new_clip_id();
            let t = s.track_mut(track).unwrap();
            t.playlist_mut().unwrap().clips.push(Clip::midi(id, "chorus boundary", 0, 480_000, seq));
            t.instrument = Some(Insert::new("subtractive_synth"));
            let player = Player::new(engine.session_arc());
            let mut app = SoundApp::new(engine, Some(player), Services::default());
            app.midi_inputs = Some(MidiInputs::with_port_names(vec![], vec!["Test DIN".into()]));
            let feed = app.midi_inputs.as_ref().unwrap().feed().clone();
            let port = feed.ports().assign("Test DIN");
            let ctx = egui::Context::default();
            let frame = |app: &mut SoundApp| { ctx.run_ui(Default::default(), |_| app.logic(&ctx)).textures_delta.clear(); };
            soundcraft_mix::ISSUE_1674_ATTACKS.lock().unwrap().clear();
            if clock {
                let result = app.run("setup.midi_clock_follow", json!({"input":"Test DIN","enabled":true,"input_offset_samples":-1440,"loss_policy":"coast"}));
                assert_eq!(result.is_ok(), clock_supported, "setup: {result:?}");
                feed.receive(port, &[0xf2, spp, 0]);
                frame(&mut app);
                feed.receive(port, &[0xfb]);
                feed.receive(port, &[0xf8]);
            } else {
                app.run("transport.locate", json!({"at":i64::from(spp)*6000})).unwrap();
                frame(&mut app);
                app.run("transport.play", json!({})).unwrap();
            }
            frame(&mut app);
            let player = app.player.as_ref().unwrap();
            if clock && !clock_supported {
                std::thread::sleep(Duration::from_millis(100));
                assert!(!player.is_playing());
                assert!(soundcraft_mix::ISSUE_1674_ATTACKS.lock().unwrap().is_empty());
                println!("Clock SPP {spp}: unsupported; no playback or note-on");
                continue;
            }
            assert!(player.is_playing());
            let deadline = Instant::now() + Duration::from_secs(5);
            while player.position() < 420_000 && Instant::now() < deadline {
                std::thread::sleep(Duration::from_millis(10));
            }
            assert!(player.position() >= 420_000, "did not render the positive control");
            player.stop();
            let events = soundcraft_mix::ISSUE_1674_ATTACKS.lock().unwrap().clone();
            let expected = if spp <= 64 { vec![49, 67] } else { vec![67] };
            println!("{} SPP {spp}: dispatched {events:?}, expected {expected:?}", if clock {"Continue"} else {"Play"});
            if expected != events { discrepancies.push((clock,spp,events)); }
        }
    }
    assert!(discrepancies.is_empty(), "unexpected note-on sequences: {discrepancies:?}");
}
