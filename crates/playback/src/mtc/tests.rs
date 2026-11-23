use super::*;
use crate::sync_clock::{DeviceTiming, Publisher, View};
use crate::{AudioState, Cmd, Shared};

use std::sync::{
    Arc,
    atomic::Ordering,
    mpsc::{Sender, channel},
};

fn session(rate: FrameRate) -> Session {
    let mut s = Session::new("sync", soundcraft_time::SampleRate::HZ_48000);
    s.frame_rate = rate;
    s.timecode_start = 0;
    s
}
fn callback(s: Session, device_rate: f64) -> (AudioState, Sender<Cmd>, View) {
    let shared = Arc::new(Shared { position: 0.into(), playing: false.into(), speed: 1000.into(), meters: Default::default() });
    let (commands, rx) = channel();
    let state = AudioState::new(rx, shared, Arc::new(s), device_rate, channel().0);
    let view = View::default();
    assert!(commands.send(Cmd::Clock(Some(Publisher::new(view.clone(), Default::default())))).is_ok());
    (state, commands, view)
}
fn block(at: Instant, position: i64, frames: i64, playing: bool, pass: u64) -> Presentation {
    Presentation {
        generation: 0,
        sample_rate: soundcraft_time::SampleRate::HZ_48000,
        system_delay_samples: 0,
        pass,
        origin: position,
        playing,
        sample: position as f64,
        heard_at: at,
        samples_per_second: 48_000.,
        limit: (position + frames) as f64,
        looped: None,
        end: None,
        lead: Some(Duration::from_millis(30)),
    }
}

#[test]
fn all_six_rates_align_eight_wire_pieces_and_session_offset_to_presentation() {
    for rate in [FrameRate::Fps23_976, FrameRate::Fps24, FrameRate::Fps25, FrameRate::Fps29_97, FrameRate::Fps29_97Drop, FrameRate::Fps30] {
        let mut s = session(rate);
        s.timecode_start = rate.samples_at_frame(3600 * rate.nominal(), s.sample_rate);
        let mut enc = Encoder::default();
        let callback = Instant::now();
        let heard = callback + Duration::from_millis(30);
        let b = block(heard, 0, 48_000, true, 0);
        let mut sent = vec![];
        let mut now = heard + Duration::from_micros(50);
        for _ in 0..24 {
            let next = enc.update(b, now, &s, &mut |at, m| sent.push((at, m.to_vec())));
            now = next.unwrap();
        }
        assert_eq!(sent[0].1, locate(3600 * rate.nominal(), rate));
        let quarter = rate.samples_per_frame(s.sample_rate) / 4.;
        let mut reader = crate::mtc_input::Reader::default();
        for (i, (stamp, msg)) in sent[1..].iter().enumerate() {
            let since = stamp.duration_since(heard);
            let expected = i as f64 * quarter / 48_000.;
            assert!((since.as_secs_f64() - expected).abs() < 1e-7, "{rate:?} {i} {since:?}");
            assert_eq!(*msg, quarters(3600 * rate.nominal() + 2 * (i as i64 / 8), rate)[i % 8]);
            let us = since.as_micros() as i64;
            reader.read(msg, us);
            if i >= 15 && i % 8 == 7 {
                let Some(crate::mtc_input::ChaseEvent::Roll(p, _)) = reader.take(us) else {
                    panic!("reader did not lock at piece {i}");
                };
                assert!(p.in_session_rate(rate).samples(s.sample_rate).abs_diff(s.timecode_start + s.sample_rate.samples(expected)) <= 1);
            }
        }
    }
}

#[test]
fn stopped_locates_drop_frame_labels_and_delayed_worker_resumes_a_whole_group() {
    let s = session(FrameRate::Fps29_97Drop);
    let now = Instant::now();
    let mut enc = Encoder::default();
    for (i, (frame, label)) in
        [(1799, [0x40, 0, 59, 29]), (1800, [0x40, 1, 0, 2]), (17_981, [0x40, 9, 59, 29]), (17_982, [0x40, 10, 0, 0])].into_iter().enumerate()
    {
        let b = block(now, s.frame_rate.samples_at_frame(frame, s.sample_rate), 0, false, i as u64);
        let mut messages = vec![];
        for _ in 0..2 {
            assert_eq!(enc.update(b, now, &s, &mut |_, m| messages.push(m.to_vec())), None);
        }
        assert_eq!(messages.len(), 1);
        assert_eq!(messages[0][5..9], label);
    }
    let b = block(now, 0, 48_000, true, 5);
    let mut messages = vec![];
    enc.update(b, now, &s, &mut |_, m| messages.push(m.to_vec()));
    let new = enc.update(b, now + Duration::from_millis(350), &s, &mut |_, m| messages.push(m.to_vec())).unwrap();
    enc.update(b, new, &s, &mut |_, m| messages.push(m.to_vec()));
    assert!(enc.stale > 0);
    assert_eq!(messages.last().unwrap()[1] >> 4, 0);
}
#[test]
fn locked_device_tracks_and_stops_during_a_ui_stall() {
    use crate::midi::MidiFeed;
    use soundcraft_model::{ChannelFormat, Clip, SourceAudio, SourceId, TrackKind};
    let mut s = session(FrameRate::Fps30);
    let track = s.add_track(TrackKind::Audio, ChannelFormat::Mono, None);
    let mut wave = vec![0.; 288_000];
    for (onset, hz) in [(225_600, 261.63), (240_000, 440.), (264_000, 739.99)] {
        for (n, v) in wave[onset..onset + 1440].iter_mut().enumerate() {
            *v = (std::f32::consts::TAU * hz * n as f32 / 48_000.).sin() * 0.5;
        }
    }
    s.pool.insert(SourceId(1), Arc::new(SourceAudio::new(craft_audio::AudioBuffer { sample_rate: 48_000, channels: vec![wave] })));
    let id = s.new_clip_id();
    s.track_mut(track).unwrap().playlist_mut().unwrap().clips.push(Clip::audio(id, "timing", SourceId(1), 0, 0, 288_000));
    let (mut audio, commands, view) = callback(s, 48_000.);
    let shared = audio.shared.clone();
    let feed = Arc::new(MidiFeed::default());
    feed.set_mtc_source(Some(0));
    commands.send(Cmd::Midi(feed.clone())).unwrap();
    let now = Instant::now();
    let lead = Duration::from_millis(25);
    // Two groups establish lock. The first audio block starts exactly at the locate.
    feed.set_clock(0);
    feed.receive(0, &locate(150, FrameRate::Fps30));
    let mut piece = 0;
    let mut buffer = [0.; 480]; // 5 ms of stereo
    let mut started = None;
    let mut attacks = Vec::new();
    let mut last_sound = -999_999;
    let mut phase = None;
    for block in 0..=2400 {
        let us = block * 5000;
        while piece * 1_000_000 / 120 <= us {
            let time = piece * 1_000_000 / 120;
            feed.set_clock(time);
            let group = quarters(152 + 2 * (piece / 8), FrameRate::Fps30);
            feed.receive(0, &group[(piece % 8) as usize]);
            piece += 1;
        }
        feed.set_clock(us);
        if started.is_none() && piece >= 16 {
            started = Some(us);
        }
        let clock = now + Duration::from_micros(us as u64);
        audio.device_timing = Some(DeviceTiming::new(clock, Some(lead), 0));
        audio.fill(&mut buffer, 2);
        if let Some(frame) = buffer.as_chunks::<2>().0.iter().position(|pair| pair[0].abs() > 0.03) {
            let onset = us + frame as i64 * 1_000_000 / 48_000;
            if onset - last_sound > 150_000 {
                attacks.push(onset);
            }
            last_sound = onset;
        }
        if started.is_some() {
            let presented = view.lock().unwrap().read(clock, true, 0).0.unwrap().sample_heard_at(clock).floor() as i64;
            if us == 800_000 {
                assert_eq!(feed.mtc_diagnostics().hard_relocates, 0, "sub-second drift must not seek");
            }
            if us == 11_935_000 {
                phase = Some(presented - ((152. * 1600.) as i64 + us * 48_000 / 1_000_000));
            }
        }
    }
    assert!(phase.unwrap().unsigned_abs() <= 480, "17 s phase: {phase:?} samples");
    assert_eq!(attacks.len(), 2, "unexpected rendered attacks: {attacks:?}");
    assert!((attacks[0] - started.unwrap()).abs() < 50_000);
    let interval = attacks[1] - attacks[0];
    assert!((interval - 500_000).abs() < 15_000, "interval {interval} us");
    assert_eq!(feed.mtc_diagnostics().hard_relocates, 1, "the protected anchor caused exactly one relaunch after sustained drift");
    assert_eq!(shared.speed.load(Ordering::Relaxed), 1000);
    feed.set_clock(12_301_000);
    audio.fill(&mut buffer, 2);
    assert!(!shared.playing.load(Ordering::Relaxed));
    assert_eq!(shared.speed.load(Ordering::Relaxed), 1000);
    println!("MTC callback-only phase={} samples, first-to-second interval={} us", phase.unwrap(), interval);
}

#[test]
fn recording_request_is_ignored_while_waiting_for_external_timecode() {
    let (mut state, cmd, _) = callback(session(FrameRate::Fps30), 48_000.);
    let feed = Arc::new(crate::midi::MidiFeed::default());
    feed.set_mtc_source(Some(0));
    cmd.send(Cmd::Midi(feed.clone())).unwrap();
    cmd.send(Cmd::Recording(true, 0)).unwrap();
    state.fill(&mut [0.; 480], 2);
    assert!(!state.is_recording());
}

#[test]
fn mtc_chase_waits_for_observed_lead_before_testing_presentation_drift() {
    let rate = FrameRate::Fps25;
    let (mut audio, tx, _) = callback(session(rate), 48_000.);
    let feed = Arc::new(crate::midi::MidiFeed::default());
    feed.set_mtc_source(Some(0));
    tx.send(Cmd::Midi(feed.clone())).unwrap();
    let now = Instant::now();
    // Model a backend with no usable timestamps, followed by an actual zero-lead report.
    // Each QF group advances 80 ms while our deliberately short callback renders only 5 ms.
    for group in 0..42 {
        for piece in 0..8 {
            let us = (group * 8 + piece) * 10_000;
            feed.set_clock(us);
            feed.receive(0, &quarters(group * 2, rate)[piece as usize]);
        }
        let measured = (group >= 22).then_some(Duration::ZERO);
        audio.device_timing = Some(DeviceTiming::new(now, measured, 0));
        audio.fill(&mut [0.; 480], 2);
        if group == 21 {
            assert!(audio.shared.playing.load(Ordering::Acquire), "input transport follows the MTC lock");
            assert_eq!(feed.mtc_diagnostics().hard_relocates, 0, "unknown audible phase cannot prove sustained drift");
        }
    }
    assert_eq!(feed.mtc_diagnostics().hard_relocates, 1, "measured zero is a valid phase reference");
}

#[test]
fn external_lock_starts_and_runs_at_unity_without_repaints() {
    for reject_next in [false, true] {
        let (mut state, cmd, view) = callback(session(FrameRate::Fps30), 48_000.);
        let feed = Arc::new(crate::midi::MidiFeed::default());
        feed.set_mtc_source(Some(0));
        cmd.send(Cmd::Midi(feed.clone())).unwrap();
        let now = Instant::now();
        for piece in 0..16 {
            let us = piece * 1_000_000 / 120;
            feed.set_clock(us);
            feed.receive(0, &quarters(2 * (piece / 8), FrameRate::Fps30)[(piece % 8) as usize]);
        }
        let mut stream = crate::sync_clock::StreamLead::default();
        let first = stream.observe(now, Some(Duration::from_millis(30)));
        state.device_timing = Some(if reject_next { stream.observe(now, None) } else { first });
        state.fill(&mut [0.; 480], 2);
        assert!(state.shared.playing.load(Ordering::Relaxed), "device callback starts on lock");

        assert!((view.lock().unwrap().read(now + Duration::from_millis(30), true, 0).0.unwrap().sample - 7440.).abs() < 1., "piece 15 at 125 ms");
        assert_eq!(state.shared.speed.load(Ordering::Relaxed), 1000);
    }
}

#[test]
fn only_mtc_transitions_wake_the_host() {
    use std::sync::atomic::AtomicUsize;
    let feed = crate::midi::MidiFeed::default();
    let count = Arc::new(AtomicUsize::new(0));
    let called = count.clone();
    feed.set_mtc_wakeup(|| {
        Box::new(move || {
            called.fetch_add(1, Ordering::Relaxed);
        })
    });
    feed.set_mtc_source(Some(0));
    for n in 0..800 {
        feed.set_clock(n * 10_000);
        feed.receive(0, &quarters(n / 8 * 2, FrameRate::Fps25)[(n % 8) as usize]);
    }
    assert_eq!(count.load(Ordering::Relaxed), 1);
    feed.receive(0, &[0xfc]);
    feed.receive(0, &locate(1, FrameRate::Fps25));
    assert_eq!(count.load(Ordering::Relaxed), 3);
    feed.receive(0, &[0xf1, 0x7f]); // invalid unpaired final piece
    assert_eq!(count.load(Ordering::Relaxed), 3);
}

#[test]
fn external_timecode_before_session_start_preserves_the_cursor_and_recovers() {
    let rate = FrameRate::Fps25;
    let mut s = session(rate);
    s.timecode_start = s.sample_rate.samples(3600.);
    let (mut audio, tx, _) = callback(s, 48_000.);
    let feed = Arc::new(crate::midi::MidiFeed::default());
    feed.set_mtc_source(Some(0));
    tx.send(Cmd::Midi(feed.clone())).unwrap();
    // Player::locate publishes the cursor and queues the device command.
    audio.shared.position.store(48_000, Ordering::Relaxed);
    tx.send(Cmd::Locate(48_000)).unwrap();
    feed.set_clock(0);
    feed.receive(0, &locate(3590 * 25, rate));
    audio.fill(&mut [0.; 480], 2);
    assert_eq!(audio.shared.position.load(Ordering::Relaxed), 48_000, "before-start locate");
    for n in 0..16 {
        feed.set_clock(n * 10_000);
        feed.receive(0, &quarters(3590 * 25 + n / 8 * 2, rate)[(n % 8) as usize]);
    }
    audio.fill(&mut [0.; 480], 2);
    assert!(!audio.shared.playing.load(Ordering::Acquire));
    assert_eq!(audio.shared.position.load(Ordering::Relaxed), 48_000, "before-start roll");
    feed.receive(0, &locate(3600 * 25, rate));
    audio.fill(&mut [0.; 480], 2);
    assert_eq!(audio.shared.position.load(Ordering::Relaxed), 0);
    for n in 0..16 {
        feed.set_clock(200_000 + n * 10_000);
        feed.receive(0, &quarters(3600 * 25 + n / 8 * 2, rate)[(n % 8) as usize]);
    }
    audio.fill(&mut [0.; 480], 2);
    assert!(audio.shared.playing.load(Ordering::Acquire));
}

#[test]
fn going_offline_before_ui_observes_roll_stops_chase_and_permits_record() {
    let (mut state, tx, _) = callback(session(FrameRate::Fps25), 48_000.);
    let feed = Arc::new(crate::midi::MidiFeed::default());
    feed.set_mtc_source(Some(0));
    tx.send(Cmd::Midi(feed.clone())).unwrap();
    for n in 0..16 {
        feed.set_clock(n * 10_000);
        feed.receive(0, &quarters(n / 8 * 2, FrameRate::Fps25)[(n % 8) as usize]);
    }
    state.fill(&mut [0.; 480], 2);
    assert!(state.shared.playing.load(Ordering::Acquire));
    let actions = tx.clone();
    state.before_commands = Some(Box::new(move || {
        feed.set_mtc_source(None);
        assert!(actions.send(Cmd::EndChase(None)).is_ok());
    }));
    state.fill(&mut [0.; 480], 2);
    assert!(!state.shared.playing.load(Ordering::Acquire), "offline must halt an unobserved chase");
    state.before_commands = None;
    tx.send(Cmd::Recording(true, 1)).unwrap();
    state.fill(&mut [0.; 480], 2);
    assert!(state.is_recording());
    tx.send(Cmd::Play { from: 4800, end: None, looped: None }).unwrap();
    tx.send(Cmd::EndChase(None)).unwrap();
    state.fill(&mut [0.; 480], 2);
    assert!(state.shared.playing.load(Ordering::Acquire), "offline must preserve local playback");
}

#[test]
fn ui_stop_from_an_earlier_lock_cannot_restart_the_new_roll() {
    let (mut state, tx, _) = callback(session(FrameRate::Fps25), 48000.);
    let feed = Arc::new(crate::midi::MidiFeed::default());
    feed.set_mtc_source(Some(0));
    tx.send(Cmd::Midi(feed.clone())).unwrap();
    let roll = |base: i64| {
        for i in 0..16 {
            feed.set_clock(base + i * 10000);
            feed.receive(0, &quarters(i / 8 * 2, FrameRate::Fps25)[(i % 8) as usize]);
        }
    };
    roll(0);
    state.fill(&mut [0.; 480], 2);
    feed.receive(0, &[0xfc]);
    let (event, old_lock) = feed.take_mtc_with_lock().unwrap();
    assert_eq!(event, crate::mtc_input::ChaseEvent::Stop);
    state.fill(&mut [0.; 480], 2);
    roll(300000);
    state.fill(&mut [0.; 480], 2);
    assert!(state.shared.playing.load(Ordering::Acquire));
    let before = state.shared.position.load(Ordering::Acquire);
    let actions = tx.clone();
    state.before_commands = Some(Box::new(move || actions.send(Cmd::EndChase(Some(old_lock))).unwrap()));
    state.fill(&mut [0.; 480], 2);
    assert_eq!(state.shared.position.load(Ordering::Acquire), before + 240);
}

#[test]
fn jam_sync_audio_free_runs_for_ten_seconds_and_seeks_only_on_the_second_new_group() {
    let (mut audio, tx, _) = callback(session(FrameRate::Fps25), 48000.);
    let feed = Arc::new(crate::midi::MidiFeed::default());
    feed.set_mtc_options(FrameRate::Fps25, 8, true, 0);
    feed.set_mtc_source(Some(0));
    tx.send(Cmd::Midi(feed.clone())).unwrap();
    audio.fill(&mut [0.; 480], 2);
    assert!(!audio.shared.playing.load(Ordering::Acquire));
    let mut first = 0;
    let mut before_jump = 0;
    for block in 0..=2094 {
        let piece = block / 2;
        feed.set_clock(block * 5000);
        if block % 2 == 0 && !(16..1016).contains(&piece) {
            let frame = piece / 8 * 2 + if piece >= 1032 { 25 } else { 0 };
            feed.receive(0, &quarters(frame, FrameRate::Fps25)[(piece % 8) as usize]);
        }
        audio.fill(&mut [0.; 480], 2);
        let cursor = audio.shared.position.load(Ordering::Acquire);
        match block {
            30 => {
                assert!(audio.shared.playing.load(Ordering::Acquire));
                first = cursor;
            }
            2030 => {
                assert_eq!(cursor - first, 480_000);
                assert_eq!(feed.mtc_diagnostics().freewheel_state, "jam sync running on internal clock");
            }
            2062 => {
                assert_eq!(feed.mtc_diagnostics().hard_relocates, 0);
                assert_eq!(feed.mtc_diagnostics().freewheel_state, "locked");
            }
            2078 => {
                assert_eq!(feed.mtc_diagnostics().hard_relocates, 0);
                before_jump = cursor;
            }
            2094 => {
                assert_eq!(feed.mtc_diagnostics().hard_relocates, 1);
                assert!(cursor - before_jump >= 48000);
            }
            _ => {}
        }
    }
}

#[test]
fn first_integer_sample_of_an_even_fractional_frame_emits_its_quarter_group() {
    let mut s = session(FrameRate::Fps29_97);
    s.timecode_start = s.frame_rate.samples_at_frame(2, s.sample_rate);
    let now = Instant::now();
    for at in [0, 1] {
        let mut enc = Encoder::default();
        let mut wire = vec![];
        let wake = enc.update(block(now, at, 48000, true, 1), now, &s, &mut |_, m| wire.push(m.to_vec()));
        assert_eq!(wire[0], locate(2, s.frame_rate));
        if at == 0 {
            assert_eq!(wire[1], quarters(2, s.frame_rate)[0]);
        } else {
            assert_eq!(wire.len(), 1);
            assert!(wake.unwrap() > now + Duration::from_millis(60));
        }
    }
}

#[test]
fn model12_acquisition_preserves_four_markers() {
    use crate::midi::MidiFeed;
    use soundcraft_model::{ChannelFormat, Clip, SourceAudio, SourceId, TrackKind};
    let mut s = session(FrameRate::Fps30);
    let track = s.add_track(TrackKind::Audio, ChannelFormat::Mono, None);
    let mut wave = vec![0.; 144000];
    for pos in [12000,36000,60000,84000] { wave[pos..pos+127].fill(0.5); }
    s.pool.insert(SourceId(1), Arc::new(SourceAudio::new(craft_audio::AudioBuffer { sample_rate: 48000, channels: vec![wave] })));
    let id=s.new_clip_id();
    s.track_mut(track).unwrap().playlist_mut().unwrap().clips.push(Clip::audio(id, "acquisition", SourceId(1), 0, 0, 144000));
    let (mut audio,commands,_) = callback(s,48000.);
    let feed=Arc::new(MidiFeed::default());feed.set_mtc_source(Some(0));
    commands.send(Cmd::Midi(feed.clone())).unwrap();
    feed.set_clock(0);feed.receive(0,&locate(0,FrameRate::Fps30));
    let events: &[(i64,u8)] = &[(100000,2), (108256,16), (116728,32), (124925,48), (133259,64), (141651,80), (149940,96), (158271,118), (166648,4), (175056,16), (183307,32), (191663,48), (200017,64), (208269,80), (216855,96), (224999,118), (233256,6), (241602,16), (250037,32), (258268,48), (266803,64), (274927,80), (283469,96), (291608,118), (300195,8), (308273,16), (316658,32), (324952,48), (333311,64), (341597,80), (349942,96), (358250,118), (366650,10), (375076,16), (383293,32), (391647,48), (399972,64), (408257,80), (416730,96), (425005,118), (433317,12), (441652,16), (449951,32), (458253,48), (466646,64), (474965,80), (483254,96), (491637,118), (499950,14), (508257,16), (516733,32), (524971,48), (533506,64), (541654,80), (549917,96), (558330,118), (566624,0), (574992,17), (583359,32), (591641,48), (599986,64), (608245,80), (616569,96), (624995,118), (633283,2), (641645,17), (650099,32), (658266,48), (666689,64), (674951,80), (683374,96), (691592,118), (699917,4), (708272,17), (716587,32), (725010,48), (733241,64), (741645,80), (749948,96), (758261,118), (766639,6), (774984,17), (783434,32), (791661,48), (800155,64), (808271,80), (816630,96), (825073,118), (833289,8), (841638,17), (849977,32), (858243,48), (866624,64), (874895,80), (883256,96), (891589,118), (899927,10), (908257,17), (916868,32), (924930,48), (933409,64), (941596,80), (950071,96), (958251,118), (966639,12), (975008,17), (983249,32), (991580,48), (999973,64), (1008254,80), (1016584,96), (1025001,118), (1033291,0), (1041652,16), (1049886,33), (1058263,48), (1066627,64), (1074972,80), (1083301,96), (1091635,118), (1099991,2), (1108245,16), (1116631,33), (1124935,48), (1133258,64), (1141590,80), (1150194,96), (1158281,118), (1166716,4), (1174898,16), (1183464,33), (1191603,48), (1200091,64), (1208252,80), (1216595,96), (1224891,118), (1233258,6), (1241647,16), (1249900,33), (1258268,48), (1266641,64), (1274931,80), (1283254,96), (1291601,118), (1299905,8), (1308273,16), (1316614,33), (1324891,48), (1333503,64), (1341541,80), (1349896,96), (1358247,118), (1366569,10), (1374971,16), (1383262,33), (1391546,48), (1400000,64), (1408255,80), (1416527,96), (1424901,118), (1433247,12), (1441655,16), (1450070,33), (1458615,48), (1466591,64), (1474883,80), (1483248,96), (1491575,118), (1499879,14), (1508285,16), (1516549,33), (1524928,48), (1533268,64), (1541576,80), (1549936,96), (1558266,118), (1566556,0), (1574925,17), (1583285,33), (1591582,48), (1599935,64), (1608268,80), (1616605,96), (1624924,118), (1633275,2), (1641680,17), (1649916,33), (1658277,48), (1667061,64), (1674949,80), (1683260,96), (1691614,118), (1700376,4), (1708260,17), (1716543,33), (1724885,48), (1733260,64), (1741557,80), (1749896,96), (1758272,118), (1766533,6), (1774896,17), (1783303,33), (1791548,48), (1799909,64), (1808290,80), (1816545,96), (1824913,118), (1833293,8), (1841652,17), (1849926,33), (1858261,48), (1866599,64), (1874970,80), (1883272,96), (1891613,118), (1899955,10), (1908274,17), (1916598,33), (1924886,48), (1933289,64), (1941545,80), (1949964,96), (1958271,118), (1966549,12), (1974896,17), (1983250,33), (1991549,48), (1999911,64), (2008261,80), (2016527,96), (2024910,118), (2033566,0), (2041663,16), (2049949,34), (2058270,48), (2066611,64), (2074900,80), (2083281,96), (2091654,118), (2099892,2), (2108252,16), (2116520,34), (2124878,48), (2133247,64), (2141540,80), (2149949,96), (2158284,118), (2166555,4), (2174945,16), (2183255,34), (2191543,48), (2199896,64), (2208277,80), (2216546,96), (2224931,118), (2233318,6), (2241563,16), (2249906,34), (2258262,48), (2266547,64), (2274911,80), (2283314,96), (2291558,118), (2299880,8), (2308275,16), (2316534,34), (2324904,48), (2333305,64), (2341552,80), (2349895,96), (2358261,118), (2366554,10), (2374894,16), (2383257,34), (2391536,48), (2399901,64), (2408224,80), (2416630,96), (2424885,118), (2433294,12), (2441553,16), (2449914,34), (2458268,48), (2466553,64), (2474904,80), (2483268,96), (2491503,118), (2499879,14), (2508258,16), (2516545,34), (2524905,48), (2533272,64), (2541553,80), (2550011,96), (2558273,118), (2566497,0), (2574909,17), (2583268,34), (2591507,48), (2599893,64)];
    let times: &[i64] = &[4023, 9160, 14040, 20019, 25035, 30019, 36017, 41030, 46035, 52110, 57033, 62013, 68013, 73026, 78012, 84095, 89011, 94020, 100017, 105016, 110014, 116013, 121007, 126028, 132026, 137025, 142048, 148027, 153046, 158046, 164041, 169039, 174067, 180062, 185031, 190054, 196030, 201026, 206057, 212039, 217039, 222063, 228045, 233031, 238021, 244031, 249024, 254039, 260050, 265022, 270022, 276034, 281022, 286023, 292040, 297026, 302023, 308038, 313041, 318035, 324050, 329026, 334027, 340060, 345057, 350046, 356031, 361020, 366036, 372049, 377113, 382045, 388041, 393120, 398016, 404016, 409040, 414014, 420016, 425038, 430029, 436014, 441033, 446016, 452010, 457043, 462026, 468014, 473024, 478027, 484018, 489018, 494039, 500032, 505035, 510034, 516032, 521050, 526032, 532105, 537012, 542031, 548082, 553025, 558038, 564024, 569021, 574032, 580021, 585013, 590027, 596020, 601023, 606014, 612012, 617013, 622049, 628036, 633039, 638020, 644037, 649024, 654010, 660026, 665019, 670109, 676036, 681027, 686106, 692027, 697078, 702079, 708053, 713082, 718113, 724147, 729105, 734124, 740063, 745027, 750019, 756038, 761028, 766034, 772140, 777030, 782022, 788016, 793028, 798013, 804018, 809029, 814016, 820069, 825151, 830014, 836011, 841042, 846023, 852062, 857025, 862017, 868031, 873020, 878019, 884066, 889037, 894016, 900013, 905009, 910052, 916025, 921014, 926030, 932028, 937010, 942044, 948019, 953016, 958023, 964018, 969007, 974101, 980116, 985033, 990031, 996040, 1001010, 1006048, 1012044, 1017018, 1022091, 1028095, 1033017, 1038018, 1044033, 1049079, 1054009, 1060027, 1065010, 1070082, 1076020, 1081013, 1086011, 1092022, 1097024, 1102009, 1108018, 1113015, 1118010, 1124032, 1129032, 1134087, 1140069, 1145032, 1150305, 1156179, 1161068, 1166025, 1172023, 1177039, 1182027, 1188061, 1193066, 1198030, 1204017, 1209056, 1214053, 1220025, 1225030, 1230034, 1236030, 1241041, 1246035, 1252017, 1257073, 1262042, 1268032, 1273060, 1278039, 1284026, 1289032, 1294035, 1300207, 1305058, 1310031, 1316018, 1321019, 1326066, 1332041, 1337017, 1342039, 1348043, 1353019, 1358146, 1364110, 1369154, 1374012, 1380043, 1385030, 1390038, 1396054, 1401138, 1406025, 1412024, 1417015, 1422006, 1428028, 1433022, 1438007, 1444024, 1449117, 1454007, 1460017, 1465082, 1470007, 1476016, 1481022, 1486006, 1492017, 1497103, 1502006, 1508057, 1513121, 1518047, 1524039, 1529044, 1534038, 1540068, 1545208, 1550063, 1556050, 1561037, 1566049, 1572052, 1577139, 1582135, 1588062, 1593078, 1598129, 1604115, 1609071, 1614034, 1620108, 1625072, 1630157, 1636047, 1641126, 1646049, 1652055, 1657048, 1662045, 1668034, 1673110, 1678046, 1684041, 1689079, 1694045, 1700050, 1705028, 1710132, 1716046, 1721052, 1726036, 1732058, 1737040, 1742044, 1748066, 1753036, 1758045, 1764043, 1769037, 1774046, 1780059, 1785071, 1790174, 1796052, 1801068, 1806091, 1812056, 1817041, 1822044, 1828043, 1833041, 1838034, 1844059, 1849042, 1854042, 1860041, 1865044, 1870052, 1876068, 1881046, 1886121, 1892097, 1897037, 1902037, 1908047, 1913040, 1918101, 1924057, 1929041, 1934046, 1940039, 1945024, 1950020, 1956050, 1961039, 1966025, 1972027, 1977030, 1982021, 1988020, 1993024, 1998036, 2004038, 2009050, 2014021, 2020026, 2025041, 2030030, 2036023, 2041053, 2046026, 2052020, 2057042, 2062028, 2068022, 2073042, 2078026, 2084019, 2089022, 2094038, 2100024, 2105040, 2110027, 2116021, 2121058, 2126072, 2132100, 2137043, 2142042, 2148034, 2153063, 2158062, 2164077, 2169047, 2174067, 2180053, 2185025, 2190046, 2196061, 2201050, 2206119, 2212065, 2217071, 2222222, 2228111, 2233146, 2238057, 2244067, 2249043, 2254037, 2260035, 2265024, 2270045, 2276066, 2281043, 2286042, 2292037, 2297051, 2302043, 2308042, 2313040, 2318039, 2324066, 2329059, 2334048, 2340045, 2345043, 2350034, 2356085, 2361063, 2366032, 2372181, 2377065, 2382030, 2388033, 2393043, 2398031, 2404044, 2409075, 2414063, 2420047, 2425043, 2430036, 2436063, 2441042, 2446037, 2452043, 2457053, 2462045, 2468039, 2473050, 2478043, 2484080, 2489036, 2494057, 2500037, 2505035, 2510038, 2516075, 2521070, 2526041, 2532044, 2537062, 2542040, 2548040];
    let now=Instant::now();let mut j=0;let mut loud=false;let mut attacks=Vec::new();
    for &us in times {
        while j<events.len() && events[j].0<=us {
            feed.set_clock(events[j].0);feed.receive(0,&[0xf1,events[j].1]);j+=1;
        }
        feed.set_clock(us);
        audio.device_timing=Some(DeviceTiming::new(now+Duration::from_micros(us as u64),Some(Duration::from_micros(15166)),0));
        let mut block=[0.;512];audio.fill(&mut block,2);
        for (i,pair) in block.chunks_exact(2).enumerate() {
            let next=pair[0].abs()>0.03;
            if next && !loud {attacks.push(us+i as i64*1000000/48000);}
            loud=next;
        }
    }
    println!("attacks us {attacks:?}, relocates {}",feed.mtc_diagnostics().hard_relocates);
    assert_eq!(attacks.len(),4,"missing coded attack at acquisition");
}
