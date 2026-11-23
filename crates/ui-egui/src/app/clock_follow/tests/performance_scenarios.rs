use super::*;
use soundcraft_midi::{Note, Sequence};
use soundcraft_model::{ChannelFormat, Clip, Insert, Session, SourceAudio, SourceId, TrackKind};
use soundcraft_time::Range;
use std::sync::Arc;

// Render a known short PCM burst through the production sampler and mixer. Detect each
// leading edge directly in the rendered signal, including double triggers or missing notes.
fn render_onsets(grid: TempoMap, ticks: impl Iterator<Item = i64>, range: Range, rate: u32) -> Vec<i64> {
    let pcm = render_stem(grid, ticks, range, rate);
    edges(&pcm, range.start).into_iter().map(|hit| hit.0).collect()
}
fn render_stem(grid: TempoMap, ticks: impl Iterator<Item = i64>, range: Range, rate: u32) -> Vec<f32> {
    let mut song = Session::default();
    song.tempo = grid;
    song.sample_rate = SampleRate::new(rate).unwrap();
    let source = SourceId(200);
    song.pool.insert(source, Arc::new(SourceAudio::new(craft_audio::AudioBuffer { sample_rate: rate, channels: vec![vec![0.8; 96]] })));
    let id = song.add_track(TrackKind::Instrument, ChannelFormat::Stereo, None);
    let clip_id = song.new_clip_id();
    let tr = song.track_mut(id).unwrap();
    let mut inst = Insert::new("sampler");
    inst.sample = Some(source);
    inst.params.insert("root_note".into(), 60.);
    inst.params.insert("attack".into(), 0.);
    tr.instrument = Some(inst);
    let mut seq = Sequence::default();
    for tick in ticks {
        seq.notes.push(Note { start: tick, length: 80, pitch: 60, channel: 0, velocity: 110, release_velocity: 64 });
    }
    tr.playlist_mut().unwrap().clips.push(Clip::midi(clip_id, "hats", 0, range.end + i64::from(rate), seq));
    soundcraft_mix::render_range(&song, range, 512).remove(0)
}
fn edges(pcm: &[f32], start: i64) -> Vec<(i64, i64)> {
    let mut attack = 0;
    let mut previous = false;
    let mut hits = Vec::new();
    for (i, &v) in pcm.iter().enumerate() {
        let sounding = v.abs() > 0.001;
        if sounding && !previous {
            attack = start + i as i64;
        } else if !sounding && previous {
            hits.push((attack, start + i as i64));
        }
        previous = sounding;
    }
    hits
}
struct Run {
    rate: u32,
    grid: TempoMap,
    expected: Vec<i64>,
    max_change: f64,
    settled_change: f64,
    false_steps: usize,
    state: State,
    at_loss: Option<State>,
    stop_sample: Option<i64>,
}
fn run(intervals: &[f64], jitter: i64, skipped: Option<std::ops::Range<usize>>, shift_us: f64, coast: bool, rate: u32) -> Run {
    let feed_owner = MidiInputs::with_port_names(vec![], vec!["DJ".into()]);
    let feed = feed_owner.feed();
    let id = feed.ports().assign("DJ");
    feed.set_clock_follow(Some(id), coast, 0, false);
    let sr = SampleRate::new(rate).unwrap();
    let mut grid = TempoMap::new(intervals[0], 4, 4).unwrap();
    let mut expected = Vec::new();
    let mut us = 20_000.;
    let origin = us as i64;
    let mut actions = Vec::new();
    let mut previous = None;
    let mut max_change = 0f64;
    let mut settled_change = 0f64;
    let mut recovering = false;
    let mut false_steps = 0;
    let mut seed = 42_u64;
    let mut state = State::Waiting;
    let mut at_loss = None;
    let mut stop_sample = None;
    feed.set_clock(origin);
    feed.receive(id, &[0xfa]);
    for (i, &bpm) in intervals.iter().enumerate() {
        if i > 0 {
            us += 2_500_000. / intervals[i - 1];
        }
        if skipped.as_ref().is_some_and(|r| i == r.end) {
            us += shift_us;
        }
        if i % 12 == 0 {
            expected.push(sr.samples((us - origin as f64) / 1e6));
        }
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        let noise = if i == 0 { 0 } else { ((seed >> 32) % (2 * jitter + 1) as u64) as i64 - jitter };
        let at = us.round() as i64 + noise;
        feed.set_clock(at);
        let missing = skipped.as_ref().is_some_and(|r| r.contains(&i));
        if !missing {
            feed.receive(id, &[0xf8]);
        }
        let s = feed.clock_follow_status(&mut actions);
        for a in actions.drain(..) {
            if matches!(a, Action::Stop) {
                stop_sample = Some(sr.samples((at - origin) as f64 / 1e6));
            }
        }
        state = s.state;
        if missing {
            at_loss = Some(state);
        }
        if s.recovering_tempo_step && !recovering {
            false_steps += 1;
        }
        recovering = s.recovering_tempo_step;
        if let Some(b) = s.bpm {
            if let Some(p) = previous
                && i >= 2
            {
                let change = f64::abs(b - p);
                max_change = max_change.max(change);
                if i >= 24 {
                    settled_change = settled_change.max(change);
                }
            }
            previous = Some(b);
        }
        update_grid(&mut grid, Some((0, origin)), 0, s, sr, sr.samples((at - origin) as f64 / 1e6 + 0.030));
        let _ = bpm;
    }
    Run { rate, grid, expected, max_change, settled_change, false_steps, state, at_loss, stop_sample }
}
fn errors(r: &Run) -> Vec<f64> {
    let end = r.expected.last().unwrap() + 24_000;
    let hits = render_onsets(r.grid.clone(), (0..r.expected.len()).map(|i| i as i64 * 480), Range::new(0, r.stop_sample.unwrap_or(end)), r.rate);
    if r.stop_sample.is_none() && r.at_loss.is_none() {
        assert_eq!(hits.len(), r.expected.len(), "unexpected number of rendered attacks");
    }
    hits.iter().zip(&r.expected).map(|(a, b)| (a - b) as f64 * 1000. / f64::from(r.rate)).collect()
}

#[test]
fn scenario_a1_pitch_fader_rendered_hats() {
    let mut meets = true;
    for (bars, delta) in [(16, 0.3), (32, 124. * 0.08), (32, -124. * 0.08)] {
        let n = bars * 96;
        let tempos: Vec<_> = (0..=2 * n).map(|i| 124. + delta * (1. - ((i as f64 / n as f64) - 1.).abs())).collect();
        for jitter in [0, 1000, 2000] {
            let r = run(&tempos, jitter, None, 0., true, 48000);
            let e = errors(&r);
            let peak = e.iter().fold(0f64, |a, b| a.max(b.abs()));
            eprintln!(
                "A1 bars={bars} delta={delta:.2} jitter_us={jitter} hats={} max_ms={peak:.3} bpm_change={:.3} bpm_change_after_beat1={:.3} recoveries={}",
                e.len(),
                r.max_change,
                r.settled_change,
                r.false_steps
            );
            meets &= peak <= 4. && r.max_change <= 0.1 && r.false_steps == 0;
        }
    }
    assert!(meets, "A1 proposed performance target");
}
#[test]
fn scenario_a2_drop_rendered_eighth_notes() {
    let mut meets = true;
    for (a, b) in [(128., 140.), (140., 128.)] {
        for transition in [384, 396] {
            for rate in [44_100, 48_000, 96_000, 192_000] {
                let tempos: Vec<_> = (0..transition + 216).map(|p| if p < transition { a } else { b }).collect();
                let r = run(&tempos, 0, None, 0., true, rate);
                let all = errors(&r);
                let first = transition / 12;
                let e = &all[first..first + 17];
                eprintln!("A2 {a}->{b} pulse={transition} rate={rate} rendered_ms={e:.3?}");
                meets &= e[1].abs() <= 10. && e[2..].iter().all(|x| x.abs() <= 4.);
            }
        }
    }
    assert!(meets, "A2 proposed performance target");
}
#[test]
fn scenario_a3_resume_pulses_without_start() {
    let mut coast_ok = false;
    for coast in [false, true] {
        let mut tempos = vec![120.; 384];
        tempos.resize(780, 128.);
        let r = run(&tempos, 0, Some(384..398), 26_562.5, coast, 48000);
        let e = errors(&r);
        let tail = e.last().unwrap();
        eprintln!(
            "A3 coast={coast} gap_us=300000 state_at_loss={:?} final={:?} hats={} master_hats={} tail_ms={tail:.3} stop_sample={:?}",
            r.at_loss,
            r.state,
            e.len(),
            r.expected.len(),
            r.stop_sample
        );
        if coast {
            coast_ok = r.state == State::Locked && tail.abs() <= 4.;
        } else {
            assert_eq!(r.state, State::Stopped);
        }
    }
    assert!(coast_ok, "A3 coast did not re-lock at the changed phase without a transport Start");
}
#[test]
fn scenario_d2_local_loop_is_ignored_under_external_positioning() {
    let mut app = SoundApp::new(Default::default(), None, crate::Services::default());
    app.midi_inputs = Some(MidiInputs::with_port_names(vec![], vec!["DJ".into()]));
    let feed = app.midi_inputs.as_ref().unwrap().feed().clone();
    let id = feed.ports().assign("DJ");
    app.run("setup.midi_clock_follow", json!({"enabled":true,"input":"DJ"})).unwrap();
    for spp in [6, 20] {
        app.run("edit.select", json!({"start":24000,"end":60000})).unwrap();
        app.run("options.loop_playback", json!({"value":true})).unwrap();
        feed.receive(id, &[0xf2, spp, 0]);
        app.service_clock_follow();
        app.handle_transport(0.);
        let origin = app.position();
        feed.receive(id, &[0xfb, 0xf8]);
        app.service_clock_follow();
        app.handle_transport(0.);
        assert!(app.is_playing());
        assert!(app.play_loop.is_none());
        assert!(app.engine.session().edit.loop_playback);
        assert_eq!(origin, i64::from(spp) * 6000);
        eprintln!("D2 SPP={spp} origin_samples={origin} local_option=true active_loop={:?}", app.play_loop);
        feed.receive(id, &[0xfc]);
        app.service_clock_follow();
        app.handle_transport(0.);
    }
}
#[test]
#[ignore = "six-hour seeded DJ set"]
fn scenario_a6_six_hours_of_seeded_steps() {
    let src = MidiInputs::with_port_names(vec![], vec!["DJ".into()]);
    let feed = src.feed();
    let id = feed.ports().assign("DJ");
    feed.set_clock_follow(Some(id), true, 0, false);
    let mut grid = TempoMap::new(120., 4, 4).unwrap();
    let sr = SampleRate::new(48000).unwrap();
    let mut actions = Vec::new();
    let mut bpm = 120.;
    let mut us = 0f64;
    let mut seed = 41_u64;
    let mut next = 180_000_000.;
    let mut changes = 0;
    let mut events = 0;
    let mut peakq = 0;
    let mut retained = [0usize; 6];
    let mut peak = [0.0_f64; 6];
    let mut audible_probes = [(0_i64, 0_i64); 6];
    let mut previous = 0.;
    feed.set_clock(0);
    feed.receive(id, &[0xfa]);
    let mut p = 0;
    while us < 21_600_000_000. {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        let at = if p == 0 { 0 } else { us.round() as i64 + ((seed >> 32) % 2001) as i64 - 1000 };
        feed.set_clock(at);
        feed.receive(id, &[0xf8]);
        if p % 6 == 0 {
            let s = feed.clock_follow_status(&mut actions);
            peakq = peakq.max(actions.len());
            actions.clear();
            update_grid(&mut grid, Some((0, 0)), 0, s, sr, sr.samples(at as f64 / 1e6 + 0.030));
            events = events.max(grid.tempos().len());
            if us - previous > 5e6 {
                let hour = (us / 3_600_000_000.) as usize;
                retained[hour] = events;
                if p % 24 == 0 {
                    audible_probes[hour] = (p * TICKS_PER_PULSE, sr.samples(us / 1e6));
                }
                peak[hour] = peak[hour].max(grid.tick_to_samples(p * TICKS_PER_PULSE, sr).abs_diff(sr.samples(us / 1e6)) as f64 / 48.);
            }
        }
        if us >= next {
            previous = us;
            bpm = 120. + ((seed >> 35) % 31) as f64;
            next = us + (180. + ((seed >> 32) % 301) as f64) * 1e6;
            changes += 1;
        }
        p += 1;
        us += 2_500_000. / bpm;
    }
    let mut audible_ms = Vec::new();
    for (tick, expected) in audible_probes {
        let actual = render_onsets(grid.clone(), std::iter::once(tick), Range::new(expected - 8000, expected + 8000), 48000);
        assert_eq!(actual.len(), 1);
        audible_ms.push((actual[0] - expected) as f64 / 48.);
    }
    let bytes = events * size_of_val(&grid.tempos()[0]);
    eprintln!(
        "A6 pulses={p} changes={changes} grid_events={events} grid_event_payload_bytes={bytes} drained_queue_peak={peakq} grid_events_per_hour={retained:?} settled_peak_by_hour_ms={peak:.3?} rendered_hour_end_ms={audible_ms:.3?}"
    );
    assert!(peak.iter().all(|x| *x < 10.), "settled phase exceeded 10 ms");
}

#[test]
fn scenario_edm_eighty_one_thirty_eighty_rendered() {
    // A single 24-bar arrangement, one continuous Clock run, all stems on its tempo grid.
    let mut tempos = vec![80.; 768];
    tempos.extend(std::iter::repeat_n(130., 768));
    tempos.extend(std::iter::repeat_n(80., 769));
    let r = run(&tempos, 0, None, 0., true, 48000);
    let range = Range::new(0, r.expected[192] + 48000);
    let mut mixed = vec![0f32; range.len() as usize];
    let mut last_release = 0;
    let mut settled = true;
    // Hats on eighths, kick on beats one and three, snare on beats two and four.
    for (name, first, stride) in [("hat", 0, 1), ("kick", 0, 4), ("snare", 2, 4)] {
        let indices: Vec<_> = (first..192).step_by(stride).collect();
        let pcm = render_stem(r.grid.clone(), indices.iter().map(|&i| i as i64 * 480), range, 48000);
        for (out, x) in mixed.iter_mut().zip(&pcm) {
            *out += x / 3.;
        }
        let hits = edges(&pcm, range.start);
        assert_eq!(hits.len(), indices.len(), "{name} count");
        let last = hits.last().unwrap();
        last_release = last_release.max(last.1);
        for (section, chunk) in hits.chunks(64 / stride).enumerate() {
            let ix = section * (64 / stride);
            let err: Vec<_> = chunk.iter().zip(&indices[ix..]).map(|(hit, i)| (hit.0 - r.expected[*i]) as f64 / 48.).collect();
            eprintln!(
                "EDM section={} bpm={} stem={name} count={} first_ms={:.3} peak_abs_ms={:.3} final_ms={:.3}",
                section + 1,
                [80, 130, 80][section],
                err.len(),
                err[0],
                err.iter().map(|x| x.abs()).fold(0f64, f64::max),
                err.last().unwrap()
            );
            settled &= err.last().unwrap().abs() <= 4.;
        }
        eprintln!("EDM {name} final_attack_sample={} final_release_sample={} final_burst_samples={}", last.0, last.1, last.1 - last.0);
    }
    let mix = edges(&mixed, range.start);
    assert_eq!(mix.len(), 192);
    let end = r.expected[192];
    assert!(last_release < end && mixed[end as usize..].iter().all(|v| v.abs() < 0.001));
    eprintln!(
        "EDM total_hats=192 total_kicks=48 total_snares=48 mixed_onsets={} song_end_sample={} final_attack_sample={} final_release_sample={last_release} silent_tail_checked_ms=1000",
        mix.len(),
        end,
        mix.last().unwrap().0
    );
    assert!(settled, "all stems should settle to within 4 ms by each section's final hit");
}
