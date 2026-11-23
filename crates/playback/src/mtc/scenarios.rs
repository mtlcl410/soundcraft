use super::*;
use crate::mtc_input::{ChaseEvent, Reader};
use soundcraft_time::SampleRate;

#[test]
fn scenario_e1_interleaved_wire_realtime() {
    let rate = FrameRate::Fps30;
    let mut failures = Vec::new();
    for rt in [0xf8, 0xfa, 0xfc] {
        let mut r = Reader::default();
        let mut full = locate(240, rate).to_vec();
        full.insert(6, rt);
        r.receive(&full, 0, 0);
        let ff = matches!(r.take(0), Some(ChaseEvent::Locate(_)));
        let mut r = Reader::default();
        for i in 0..16 {
            let msg = quarters(i / 8 * 2, rate)[i as usize % 8];
            r.receive(&[msg[0], rt, msg[1]], i * 8333, i * 8333);
        }
        let qf = matches!(r.take(125000), Some(ChaseEvent::Roll(_, _)));
        eprintln!("E-1 {rt:x} full={ff} quarter={qf}");
        if !ff || !qf {
            failures.push(rt);
        }
    }
    assert!(failures.is_empty(), "interleaved bytes lost MTC: {failures:?}");
}

#[test]
fn scenario_e2_reject_invalid_timecode() {
    let mut frames = vec![];
    let valid = locate(0, FrameRate::Fps30).to_vec();
    frames.push(valid[..9].to_vec());
    let mut extra = valid.clone();
    extra.insert(5, 1);
    frames.push(extra);
    for (index, byte) in [(2, 128), (5, 128), (5, 0x60 | 24), (6, 60), (7, 60), (8, 30), (8, 128)] {
        let mut msg = valid.clone();
        msg[index] = byte;
        frames.push(msg);
    }
    for msg in &frames {
        let mut r = Reader::default();
        r.receive(msg, 0, 0);
        assert!(r.take(0).is_none(), "{msg:?}");
    }
    for pattern in [&[0, 1, 2, 4, 5, 6, 7][..], &[0, 1, 4, 3, 2, 5, 6, 7][..], &[7, 6, 5, 4, 3, 2, 1, 0][..]] {
        let mut r = Reader::default();
        for n in 0..3 {
            let q = quarters(n * 2, FrameRate::Fps30);
            for (i, &piece) in pattern.iter().enumerate() {
                let stamp = (n * 8 + i as i64) * 8333;
                r.receive(&q[piece], stamp, stamp);
                assert!(r.take(stamp).is_none());
            }
        }
    }
    eprintln!("E-2 rejected {} malformed SysEx plus missing, shuffled, backward QF groups", frames.len());
}

#[test]
fn scenario_e5_ten_million_reader_bytes() {
    let mut r = Reader::default();
    let mut seed = 0x3f5da90c4bfe11u64;
    let mut processed = 0usize;
    let mut packets = 0;
    let mut events = 0;
    while processed < 10_000_000 {
        let mut buf = [0u8; 12];
        for b in &mut buf {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            *b = seed as u8;
        }
        let len = (1 + buf[11] as usize % 12).min(10_000_000 - processed);
        if packets % 5 == 0 {
            buf[0] = 0xf1;
        } else if packets % 7 == 0 {
            buf[0] = 0xf0;
        }
        r.receive(&buf[..len], packets, packets);
        events += usize::from(r.take(packets).is_some());
        packets += 1;
        processed += len;
    }
    eprintln!("E-5 processed={processed} packets={packets} events={events} reader_bytes={}", std::mem::size_of::<Reader>());
}
const RATES: [FrameRate; 6] =
    [FrameRate::Fps23_976, FrameRate::Fps24, FrameRate::Fps25, FrameRate::Fps29_97, FrameRate::Fps29_97Drop, FrameRate::Fps30];
fn stamp(piece: i64, rate: FrameRate) -> i64 {
    let (n, d) = rate.rational();
    (piece as f64 * 1e6 * d as f64 / (4. * n as f64)).round() as i64
}
fn decode_group(r: &mut Reader, frame: i64, first_piece: i64, rate: FrameRate) -> Option<ChaseEvent> {
    let group = quarters(frame, rate);
    for (i, m) in group.iter().enumerate() {
        let t = stamp(first_piece + i as i64, rate);
        r.receive(m, t, t);
    }
    r.take(stamp(first_piece + 7, rate))
}

#[test]
fn scenario_a9_b2_generator_restarts() {
    let rate = FrameRate::Fps25;
    let song = session(rate);
    let mut enc = Encoder::default();
    let base = Instant::now();
    let mut follower = Reader::default();
    follower.options.rate = rate;
    for rolling in [true, false] {
        let count = if rolling { 20 } else { 30 };
        let mut max_lock = 0;
        let mut ff = 0;
        let mut qfs = 0;
        let mut parked_cues = 0;
        for i in 0..count {
            let frame = if rolling { 25 * (10 + (i * 7) % 11) } else { 25 * 16 }; // Return to the same point, eight 4/4 bars back at 120 BPM.
            let host = base + Duration::from_secs((i + if rolling { 0 } else { 100 }) as u64 * 20);
            let sr = song.sample_rate;
            let start = sr.samples(frame as f64 / 25.);
            if !rolling {
                // Prior pass actually reaches the end of eight bars.
                let park = block(host - Duration::from_millis(20), start + 16 * 48000, 0, false, 3 * i as u64 + 1);
                enc.update(park, park.heard_at, &song, &mut |at, m| {
                    let t = at.duration_since(base).as_micros() as i64;
                    follower.receive(m, t, t);
                });
                let cue = block(host - Duration::from_millis(10), start, 0, false, 3 * i as u64 + 2);
                let mut cues = Vec::new();
                enc.update(cue, cue.heard_at, &song, &mut |at, m| {
                    let t = at.duration_since(base).as_micros() as i64;
                    follower.receive(m, t, t);
                    cues.push(m.to_vec());
                });
                assert_eq!(cues, vec![locate(frame, rate).to_vec()]);
                parked_cues += 1;
            }
            let b = block(host, start, if rolling { 48_000 } else { 16 * 48000 }, true, if rolling { i as u64 + 501 } else { 3 * i as u64 + 3 });
            let mut packets = Vec::new();
            let mut now = host;
            for _ in 0..if rolling { 40 } else { 1600 } {
                now = enc.update(b, now, &song, &mut |t, m| packets.push((t, m.to_vec()))).unwrap_or(now + Duration::from_millis(10));
            }
            assert_eq!(packets[0].1, locate(frame, rate));
            assert_eq!(packets.iter().filter(|(_, m)| m[0] == 0xf0).count(), 1);
            ff += 1;
            let mut locked = None;
            let mut prev = None;
            for (n, (at, msg)) in packets.iter().enumerate() {
                let us = at.duration_since(base).as_micros() as i64;
                follower.receive(msg, us, us);
                if n > 0 {
                    let frame_offset = (n as i64 - 1) / 8 * 2;
                    let first = ((frame + 1) / 2) * 2;
                    assert_eq!(*msg, quarters(first + frame_offset, rate)[(n - 1) % 8]);
                    qfs += 1;
                }
                if let Some(ChaseEvent::Roll(pos, _)) = follower.take(us) {
                    let s = pos.samples(sr);
                    assert!(prev.is_none_or(|old| s > old));
                    prev = Some(s);
                    locked.get_or_insert(at.duration_since(host).as_micros());
                }
            }
            max_lock = max_lock.max(locked.unwrap());
        }
        eprintln!(
            "{} passes={count} parked_locates={parked_cues} relaunch_fullframes={ff} quarters={qfs} maximum_relock_us={max_lock}",
            if rolling { "A-9" } else { "B-2" }
        );
        if !rolling {
            assert!(max_lock <= 320_000);
        }
    }
}

#[test]
fn scenario_c1_c8_ten_minutes_six_rates() {
    let mut total_differences = 0;
    for rate in RATES {
        let mut r = Reader::default();
        r.options.rate = rate;
        r.source = Some(0);
        let mut stationary = Reader::default();
        let mut max = 0;
        let mut groups = 0;
        let mut frames = 0;
        let mut mismatches = 0;
        let mut wrong = [0usize; 4];
        let mut worst = 0u64;
        let mut first = None;
        let total = 600 * rate.rational().0 as i64 / rate.rational().1 as i64;
        for frame in 0..total {
            let ff = locate(frame, rate);
            let t = stamp(frame * 4, rate);
            stationary.receive(&ff, t, t);
            let Some(ChaseEvent::Locate(pos)) = stationary.take(t) else { panic!("invalid literal frame {frame} {rate:?}") };
            for (i, hz) in [44100, 48000, 96000, 192000].into_iter().enumerate() {
                let sr = SampleRate::new(hz).unwrap();
                let expected = rate.samples_at_frame(frame, sr);
                let actual = pos.session_sample(rate, sr, 0, 0);
                if actual != expected {
                    wrong[i] += 1;
                    worst = worst.max(actual.abs_diff(expected));
                    first.get_or_insert((hz, frame, actual, expected));
                }
            }
            frames += 1;
            if frame % 2 != 0 {
                continue;
            }
            let ev = decode_group(&mut r, frame, frame * 4, rate);
            if frame > 0 {
                let Some(ChaseEvent::Roll(p, _)) = ev else { panic!("no lock {rate:?} frame {frame}") };
                for hz in [44100, 48000, 96000, 192000] {
                    let sr = SampleRate::new(hz).unwrap();
                    let expected = ((frame as f64 + 1.75) * rate.samples_per_frame(sr)).round() as i64;
                    max = max.max(p.in_session_rate(rate).samples(sr).abs_diff(expected));
                }
                groups += 1;
                mismatches += usize::from(r.incoming_status().1.is_some());
            }
        }
        eprintln!(
            "C-1/C-8 {rate:?} full_frames={frames} whole_mismatches_by_sample_rate={wrong:?} worst_whole_samples={worst} first={first:?} rolling_groups={groups} max_quarter_error_samples={max} rate_warnings={mismatches}"
        );
        total_differences += wrong.iter().sum::<usize>();
        assert_eq!(mismatches, 0);
        assert!(max <= 1);
        r.options.rate = if rate == FrameRate::Fps25 { FrameRate::Fps30 } else { FrameRate::Fps25 };
        assert!(r.incoming_status().1.is_some());
    }
    assert_eq!(total_differences, 0, "MTC locates must agree with Session Setup at whole frames");
}

#[test]
fn scenario_c2_c3_midnight_and_df() {
    for (rate, frame, pair, wrap) in [
        (FrameRate::Fps29_97Drop, 1799, ([0x40, 0, 59, 29], [0x40, 1, 0, 2]), false),
        (FrameRate::Fps29_97Drop, 17981, ([0x40, 9, 59, 29], [0x40, 10, 0, 0]), false),
        (FrameRate::Fps30, 107999, ([0x60, 59, 59, 29], [0x61, 0, 0, 0]), false),
        (FrameRate::Fps30, 2591999, ([0x77, 59, 59, 29], [0x60, 0, 0, 0]), true),
    ] {
        let mut pos = Vec::new();
        let mut r = Reader::default();
        for (n, expected) in [pair.0, pair.1].iter().enumerate() {
            let msg = locate(frame + n as i64, rate);
            assert_eq!(&msg[5..9], expected);
            r.receive(&msg, 0, 0);
            let Some(ChaseEvent::Locate(p)) = r.take(0) else { panic!("no locate") };
            pos.push(p.samples(SampleRate::HZ_48000));
        }
        let mut r = Reader::default();
        r.options.rate = rate;
        r.source = Some(0);
        let mut rolls = vec![];
        for group in 0..5 {
            if let Some(ChaseEvent::Roll(p, _)) = decode_group(&mut r, frame - 5 + group * 2, group * 8, rate) {
                rolls.push(p.samples(SampleRate::HZ_48000));
            }
        }
        eprintln!("C2/C3 {rate:?} source_frame={frame} position_delta={} roll_positions={rolls:?}", pos[1] - pos[0]);
        assert_eq!(rolls.len(), 4);
        if wrap {
            assert!(rolls.windows(2).any(|p| p[0] > p[1]));
        } else {
            assert!(rolls.windows(2).all(|p| p[0] < p[1]));
            assert!((1600..=1602).contains(&(pos[1] - pos[0])));
        }
    }
}

#[test]
fn scenario_b3_loss_modes() {
    for (frames, jam) in [(0, false), (4, false), (8, false), (40, false), (8, true)] {
        let rate = FrameRate::Fps25;
        let (mut audio, tx, _) = callback(session(rate), 48000.);
        let input = Arc::new(crate::midi::MidiFeed::default());
        input.set_mtc_options(rate, frames, jam, 0);
        input.set_mtc_source(Some(0));
        tx.send(Cmd::Midi(input.clone())).unwrap();
        let mut stop = None;
        let mut origin = 0;
        let mut end = 0;
        for i in 0..=1030 {
            let us = i * 10000;
            input.set_clock(us);
            if i <= 31 {
                input.receive(0, &quarters(i / 8 * 2, rate)[i as usize % 8]);
            }
            audio.fill(&mut [0.; 960], 2);
            if i == 30 {
                origin = audio.shared.position.load(Ordering::Acquire);
            }
            if i > 31 && !audio.shared.playing.load(Ordering::Acquire) {
                stop.get_or_insert(us - 310000);
            }
            end = audio.shared.position.load(Ordering::Acquire);
        }
        let drift = end - origin - 480000;
        eprintln!("B-3 frames={frames} jam={jam} first_stopped_us={stop:?} jam_drift_samples={:?}", jam.then_some(drift));
        if jam {
            assert_eq!(stop, None);
            assert_eq!(drift, 0);
        } else {
            assert_eq!(stop, Some(i64::from(if frames == 0 { 2 } else { frames }) * 40000));
        }
    }
}

#[test]
#[ignore = "two hours per drift sign of offline PCM; run explicitly"]
fn scenario_c4_two_hour_drift_render() {
    for ppm in [-50, 50] {
        let rate = FrameRate::Fps30;
        let mut s = session(rate);
        s.edit.click = true;
        let (mut audio, tx, _) = callback(s, 48000.);
        let feed = Arc::new(crate::midi::MidiFeed::default());
        feed.set_mtc_source(Some(0));
        tx.send(Cmd::Midi(feed.clone())).unwrap();
        let base = Instant::now();
        let mut pcm = [0.; 960];
        let mut piece = 0;
        let mut max_err = 0;
        let mut last_on = -1_000_000i64;
        let mut prev_relocs = 0;
        let mut jumps = Vec::new();
        let mut prev_pos = 0;
        let mut clicks = 0;
        let mut last_err = 0;
        let mut last_beat: Option<i64> = None;
        let mut duplicates = 0;
        let mut missed = 0;
        let blocks = (720000. * (1. + f64::from(ppm) * 1e-6)).ceil() as i64;
        for k in 0..blocks {
            let us = (k * 10000) as f64 / (1. + f64::from(ppm) * 1e-6);
            let us = us.round() as i64;
            while stamp(piece, rate) <= us {
                let t = stamp(piece, rate);
                feed.set_clock(t);
                feed.receive(0, &quarters((piece / 8) * 2, rate)[piece as usize % 8]);
                piece += 1;
            }
            feed.set_clock(us);
            audio.device_timing = Some(DeviceTiming::new(base + Duration::from_micros(us as u64), Some(Duration::ZERO), 0));
            audio.fill(&mut pcm, 2);
            let pos = audio.shared.position.load(Ordering::Relaxed);
            let reloc = feed.mtc_diagnostics().hard_relocates;
            if reloc != prev_relocs {
                jumps.push((us, pos - prev_pos - 480));
            }
            if us > 2_000_000
                && us - last_on > 200000
                && let Some(offset) = pcm.chunks_exact(2).position(|ch| ch[0].abs() > 0.01)
            {
                let t = us + (offset as f64 * 1e6 / (48000. * (1. + f64::from(ppm) * 1e-6))).round() as i64;
                let beat = (t + 250000) / 500000;
                if let Some(old) = last_beat {
                    duplicates += usize::from(old == beat);
                    missed += (beat - old - 1).max(0);
                }
                last_beat = Some(beat);
                let error = t - beat * 500000;
                last_err = error;
                max_err = max_err.max(error.abs());
                last_on = t;
                clicks += 1;
            }
            prev_relocs = reloc;
            prev_pos = pos;
        }
        let diag = feed.mtc_diagnostics();
        assert!(audio.shared.playing.load(Ordering::Acquire));
        assert_eq!(diag.locks, 1);
        eprintln!(
            "C-4 ppm={ppm} source_interval_us={} clicks={clicks} duplicate_beats={duplicates} missing_beats={missed} peak_audible_offset_us={max_err} last_offset_us={last_err} losses={} relocations={} jumps_us_samples={jumps:?}",
            stamp(piece, rate),
            diag.losses,
            diag.hard_relocates
        );
        assert_eq!(diag.losses, 0);
        assert!(clicks > 14000);
    }
}
#[test]
fn scenario_b4_record_while_generating() {
    use crate::record::{Recorder, TakeFiles};
    let song = session(FrameRate::Fps25);
    let (mut audio, tx, view) = callback(song.clone(), 48000.);
    let mut enc = Encoder::default();
    let (mut rec, mut insert) = Recorder::mtc_scenario_input();
    let dir = std::env::temp_dir().join(format!("mtc-b4-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let a = dir.join("L.wav");
    let b = dir.join("R.wav");
    let mut packets = vec![];
    let base = Instant::now();
    tx.send(Cmd::Play { from: 0, end: None, looped: None }).unwrap();
    for k in 0..200 {
        if k == 25 {
            tx.send(Cmd::Recording(true, 0)).unwrap();
            rec.arm(
                vec![(soundcraft_model::TrackId(1), vec![0], a.clone()), (soundcraft_model::TrackId(2), vec![1], b.clone())],
                TakeFiles { samples: u64::MAX, part: |_, _| unreachable!() },
            )
            .unwrap();
        }
        let mut input = [0.; 960];
        if [50, 100, 175].contains(&k) {
            input[2 * 13] = 0.5;
            input[2 * 64 + 1] = 0.75;
        }
        insert(&input);
        let now = base + Duration::from_millis(k * 10);
        audio.device_timing = Some(DeviceTiming::new(now, Some(Duration::ZERO), 0));
        audio.fill(&mut [0.; 960], 2);
        if k >= 25 {
            assert!(audio.is_recording());
        }
        let p = view.lock().unwrap().read(now, true, 0).0.unwrap();
        enc.update(p, now, &song, &mut |t, m| packets.push((t, m.to_vec())));
    }
    let (takes, problem) = rec.finish();
    assert!(problem.is_none());
    assert_eq!(takes.len(), 2);
    for (path, delay) in [(a, 13), (b, 64)] {
        let wav = craft_audio::decode(&std::fs::read(path).unwrap(), None).unwrap().1;
        let attacks = wav.channels[0].iter().enumerate().filter(|(_, x)| x.abs() > 0.4).map(|(i, _)| i as i64 + 25 * 480).collect::<Vec<_>>();
        let expected = [50 * 480 + delay, 100 * 480 + delay, 175 * 480 + delay];
        assert_eq!(attacks, expected);
        eprintln!("B-4 WAV attacks timeline_samples={attacks:?} offset_samples=0");
    }
    assert_eq!(packets.iter().filter(|(_, m)| m[0] == 0xf0).count(), 1);
    let times = packets.iter().filter(|(_, m)| m[0] == 0xf1).map(|(t, _)| *t).collect::<Vec<_>>();
    assert_eq!(times.len(), 200);
    assert!(times.windows(2).all(|w| w[1] - w[0] == Duration::from_millis(10)));
    eprintln!("B-4 FF=1 quarters={} period_us=10000 record_start_ms=250", times.len());
}
#[test]
fn scenario_a10_render_continues_across_stream_reset() {
    use soundcraft_model::{ChannelFormat, Clip, SourceAudio, SourceId, TrackKind};
    let mut song = session(FrameRate::Fps25);
    let track = song.add_track(TrackKind::Audio, ChannelFormat::Mono, None);
    let wave = (0..96000).map(|i| if i % 48 < 24 { 0.25 } else { -0.25 }).collect::<Vec<_>>();
    song.pool.insert(SourceId(1), Arc::new(SourceAudio::new(craft_audio::AudioBuffer { sample_rate: 48000, channels: vec![wave] })));
    let id = song.new_clip_id();
    song.track_mut(track).unwrap().playlist_mut().unwrap().clips.push(Clip::audio(id, "Reset", SourceId(1), 0, 0, 96000));
    let (mut test, t_test, _) = callback(song.clone(), 48000.);
    let (mut control, t_control, _) = callback(song, 48000.);
    for tx in [t_test, t_control] {
        tx.send(Cmd::Play { from: 0, end: None, looped: None }).unwrap();
    }
    let now = Instant::now();
    let mut hardware = crate::sync_clock::StreamLead::default();
    let mut energy = 0.;
    for ms in (0..1000).step_by(10) {
        let t = now + Duration::from_millis(ms);
        if ms == 300 {
            hardware = Default::default();
        }
        test.device_timing = Some(hardware.observe(t, (ms < 250 || ms >= 500).then_some(Duration::ZERO)));
        control.device_timing = Some(DeviceTiming::new(t, Some(Duration::ZERO), 0));
        let mut measured = [0.; 960];
        let mut expected = [0.; 960];
        test.fill(&mut measured, 2);
        control.fill(&mut expected, 2);
        assert_eq!(measured, expected);
        let chunk = measured.iter().map(|x| x * x).sum::<f32>();
        assert!(chunk > 1.);
        energy += chunk;
    }
    eprintln!("A-10 audio frames=48000 channels=2 sample_differences=0 signal_energy={energy:.2}");
}
