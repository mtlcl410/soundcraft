use super::*;

fn random(seed: &mut u64) -> u64 {
    *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
    *seed >> 32
}

#[test]
fn scenario_e1_clock_interleaved_in_timecode() {
    let mut f = Follower::default();
    f.receive(&[0xf0, 0x7f, 0xfa, 0x7f, 1, 1, 0xf8, 0x60, 0, 0, 0, 0xfc, 0xf7], 100);
    assert_eq!(f.take(), Some(Action::Locate(0)));
    assert_eq!(f.take(), Some(Action::Play { pulse: 0, at: 100 }));
    assert_eq!(f.take(), Some(Action::Stop));
    f.receive(&[0xf1, 0xfa, 0, 0xf1, 0xf8, 0x10, 0xf1, 0xfc, 0x20], 200);
    assert_eq!(f.take(), Some(Action::Locate(0)));
    assert_eq!(f.take(), Some(Action::Play { pulse: 0, at: 200 }));
    assert_eq!(f.take(), Some(Action::Stop));
    assert!(f.take().is_none());
}
#[test]
fn scenario_e3_song_pointer_during_play_and_at_rest() {
    let mut f = Follower::default();
    f.receive(&[0xf2, 0x80, 1, 0xf2, 1, 0x90, 2], 0);
    assert!(f.take().is_none());
    f.receive(&[0xf2, 0x7f, 0x7f, 0xf2, 3, 0], 100);
    assert_eq!(f.take(), Some(Action::Locate(98_298)));
    assert_eq!(f.take(), Some(Action::Locate(18)));
    f.receive(&[0xfb, 0xf8], 200);
    assert_eq!(f.take(), Some(Action::Play { pulse: 18, at: 200 }));
    f.receive(&[0xf2, 5, 0], 300);
    assert!(f.take().is_none());
    eprintln!("E3 invalid=0 locates; consecutive=98298,18; Continue=18; while playing=0 locates");
}
#[test]
fn scenario_e4_extreme_clock_rates() {
    for (period, n) in [(10_000_000, 60), (100, 100_000)] {
        let mut f = Follower::default();
        f.receive(&[0xfa], 0);
        let mut high = 0;
        for i in 0..n {
            f.receive(&[0xf8], i * period);
            high = high.max(f.count);
            while f.take().is_some() {}
        }
        let snap = f.snapshot(n * period);
        eprintln!("E4 interval_us={period} pulses={n} state={:?} bpm={:?} queue_peak={high}", snap.state, snap.bpm);
        assert!(high <= 2);
        assert!(snap.bpm.is_none());
    }
}
#[test]
fn scenario_e5_clock_ten_million_stream_bytes() {
    let mut f = Follower::default();
    let mut seed = 20261122;
    let mut high = 0;
    for i in 0..10_000_000 {
        f.receive(&[random(&mut seed) as u8], i * 11);
        high = high.max(f.count);
        if i % 50 == 0 {
            while f.take().is_some() {}
        }
    }
    eprintln!("E5 bytes=10000000 queue_peak={high}/{} reader_bytes={}", f.events.len(), size_of::<Follower>());
    assert!(high <= f.events.len());
}
#[test]
fn scenario_a4_ten_minutes_of_bunched_clock() {
    let mut worst = 0.0_f64;
    for count in 3..=5 {
        let mut f = Follower::default();
        f.receive(&[0xfa], 0);
        let mut min = f64::MAX;
        let mut max = 0.0_f64;
        let mut false_steps = 0;
        let mut active = false;
        for p in 0..28_800 {
            let at = (((p / count) * count) as f64 * 2_500_000. / 120.).round() as i64 + (p % count) * 200;
            f.receive(&[0xf8], at);
            assert_eq!(f.state, State::Locked);
            let s = f.snapshot(at);
            if p > 192 {
                let b = s.bpm.unwrap();
                min = min.min(b);
                max = max.max(b);
                if !active && s.recovering_tempo_step {
                    false_steps += 1;
                }
            }
            active = s.recovering_tempo_step;
        }
        eprintln!("A4 group={count} pulses=28800 bpm={min:.4}..{max:.4} false_steps={false_steps} dropouts={}", f.dropouts);
        worst = worst.max(max - min);
        assert_eq!(false_steps, 0);
    }
    assert!(worst <= 0.1, "proposed steady display tolerance; span={worst}");
}
#[test]
fn scenario_a5_random_phase_transport() {
    let mut seed = 55_u64;
    let mut r = Follower::default();
    let mut at = 0;
    let mut starts = 0;
    let mut resumes = 0;
    for _ in 0..50 {
        for _ in 0..(1 + random(&mut seed) % 24) {
            at += 20_833;
            r.receive(&[0xf8], at);
            assert!(r.take().is_none());
        }
        r.receive(&[0xfa], at + 1);
        assert_eq!(r.take(), Some(Action::Locate(0)));
        at += 20_833;
        r.receive(&[0xf8], at);
        assert_eq!(r.take(), Some(Action::Play { pulse: 0, at }));
        starts += 1;
        r.receive(&[0xfc], at + 1);
        assert_eq!(r.take(), Some(Action::Stop));
        let spp = (random(&mut seed) % 1000) as i64;
        r.receive(&[0xf2, (spp % 128) as u8, (spp / 128) as u8], at + 2);
        assert_eq!(r.take(), Some(Action::Locate(6 * spp)));
        r.receive(&[0xfb], at + 3);
        at += 20_833;
        r.receive(&[0xf8], at);
        assert_eq!(r.take(), Some(Action::Play { pulse: 6 * spp, at }));
        resumes += 1;
        r.receive(&[0xfc], at + 1);
        assert_eq!(r.take(), Some(Action::Stop));
    }
    eprintln!("A5 starts={starts} continuations={resumes} stops=100; parked clocks never played");
}
#[test]
fn scenario_a5_notes_released_across_random_stops() {
    use crate::{AudioState, Cmd, PreparedInstance, Shared};
    use soundcraft_dsp::Plugin;
    use soundcraft_model::{ChannelFormat, Clip, Insert, Session, TrackKind};
    use std::sync::{
        Arc, Mutex,
        atomic::{AtomicBool, AtomicI64, AtomicU32},
        mpsc::channel,
    };
    #[derive(Default)]
    struct Counts {
        on: usize,
        off: usize,
        by_reset: usize,
        active: bool,
    }
    struct Keys {
        counts: Arc<Mutex<Counts>>,
        inner: Box<dyn Plugin>,
    }
    impl Plugin for Keys {
        fn info(&self) -> &'static soundcraft_dsp::PluginInfo {
            self.inner.info()
        }
        fn prepare(&mut self, sr: f32, mb: usize, ch: usize) {
            self.inner.prepare(sr, mb, ch)
        }
        fn reset(&mut self) {
            let mut c = self.counts.lock().unwrap();
            c.by_reset += usize::from(c.active);
            c.active = false;
        }
        fn set_param(&mut self, id: &str, x: f32) -> bool {
            self.inner.set_param(id, x)
        }
        fn param(&self, id: &str) -> Option<f32> {
            self.inner.param(id)
        }
        fn process(&mut self, io: &mut [Vec<f32>], n: usize) {
            for ch in io {
                ch[..n].fill(0.)
            }
        }
        fn note_on(&mut self, _: usize, _: u8, _: u8) {
            let mut c = self.counts.lock().unwrap();
            c.on += 1;
            c.active = true;
        }
        fn note_off(&mut self, _: usize, _: u8) {
            let mut c = self.counts.lock().unwrap();
            c.off += 1;
            c.active = false;
        }
    }
    let mut song = Session::default();
    let track = song.add_track(TrackKind::Instrument, ChannelFormat::Stereo, None);
    let cid = song.new_clip_id();
    let tr = song.track_mut(track).unwrap();
    let notes: Vec<_> =
        (0..64).map(|i| serde_json::json!({"start":i*240,"length":80,"channel":0,"velocity":110,"pitch":60,"release_velocity":64})).collect();
    let seq = serde_json::from_value(serde_json::json!({"notes":notes,"ctrls":[]})).unwrap();
    tr.playlist_mut().unwrap().clips.push(Clip::midi(cid, "Show", 0, 384000, seq));
    tr.instrument = Some(Insert::new("clap:test.keys"));
    let counts = Arc::new(Mutex::new(Counts::default()));
    let probe = Keys { counts: counts.clone(), inner: soundcraft_dsp::create("gain").unwrap() };
    let shared =
        Arc::new(Shared { position: AtomicI64::new(0), playing: AtomicBool::new(false), speed: AtomicU32::new(1000), meters: Mutex::default() });
    let (tx, rx) = channel();
    let song = Arc::new(song);
    let mut st = AudioState::new(rx, shared, song.clone(), 48000., channel().0);
    tx.send(Cmd::Session(
        1,
        song.clone(),
        vec![PreparedInstance { track, slot: soundcraft_mix::INSTRUMENT_SLOT, id: "clap:test.keys".into(), ch: 2, plugin: Box::new(probe) }],
    ))
    .unwrap();
    let mut seed = 55;
    let mut r = Follower::default();
    let mut at = 0;
    for _ in 0..50 {
        for _ in 0..(1 + random(&mut seed) % 24) {
            at += 20_833;
            r.receive(&[0xf8], at);
            assert!(r.take().is_none());
        }
        let spp = (random(&mut seed) % 64) as u8;
        for (msg, expected) in [(vec![0xfa], 0), (vec![0xf2, spp, 0, 0xfb], i64::from(spp) * 6)] {
            at += 20_833;
            r.receive(&msg, at);
            r.receive(&[0xf8], at);
            assert_eq!(r.take(), Some(Action::Locate(expected)));
            assert_eq!(r.take(), Some(Action::Play { pulse: expected, at }));
            let origin = expected * 1000;
            tx.send(Cmd::PlayClock { origin, render_from: origin }).unwrap();
            st.fill(&mut vec![0.; 2 * (128 + (random(&mut seed) % 3700) as usize)], 2);
            r.receive(&[0xfc], at + 1);
            assert_eq!(r.take(), Some(Action::Stop));
            tx.send(Cmd::Stop).unwrap();
            st.fill(&mut [0.; 512], 2);
            assert!(!counts.lock().unwrap().active);
        }
    }
    let c = counts.lock().unwrap();
    eprintln!("A5 plugin note_on={} explicit_off={} released_by_reset={} held_after_stop={}", c.on, c.off, c.by_reset, c.active);
    assert_eq!(c.on, 100);
    assert_eq!(c.on, c.off + c.by_reset);
    assert_eq!(c.on, c.off, "literal note-off-for-every-note-on target");
}
