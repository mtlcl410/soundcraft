use soundcraft_playback::midi::MidiInputs;
use soundcraft_playback::clock_follow::{Action, Snapshot, State};
use soundcraft_time::{SampleRate, TICKS_PER_QUARTER, TempoMap};

const TICKS_PER_PULSE: i64 = TICKS_PER_QUARTER / 24;

fn update_grid(grid: &mut TempoMap, anchor: Option<(i64, i64)>, waiting_tick: i64, s: Snapshot, sr: SampleRate, render_until: i64) -> bool {
    let Some(bpm) = s.bpm else { return false };
    let Some((origin, stamp)) = anchor else {
        if s.state == State::Waiting && (grid.tempo_at_tick(waiting_tick) - bpm).abs() >= 0.05 {
            let _ = grid.set_tempo(waiting_tick, bpm);
            return true;
        }
        return false;
    };
    let tick = s.pulse.saturating_mul(TICKS_PER_PULSE);
    let writable = grid.samples_to_ticks(render_until, sr).saturating_add(1);
    // A batched acceleration can report a pulse far beyond the committed audio.
    // Start the confirmed correction at the first writable tick in that case.
    let edit = if render_until > 0 && (s.packed_delivery || s.braking) && s.recovering_tempo_step {
        writable.max(origin.saturating_mul(TICKS_PER_PULSE))
    } else {
        tick.max(writable)
    };
    // On a slowdown the audio cursor can be several Clock pulses ahead of the wire.
    // Compare against the writable position while slewing so an earlier correction
    // cannot hold up the next one after playback has already crossed it.
    let check_tick = if s.recovering_tempo_step { edit } else { tick };
    if grid.tempos().last().is_some_and(|event| event.tick > check_tick) {
        return false;
    }
    let before = grid.tempos().partition_point(|event| event.tick <= check_tick);
    let last_edit_tick = grid.tempos()[..before].last().map_or(0, |event| event.tick);
    let since_edit = check_tick.saturating_sub(last_edit_tick);
    let slope = grid.tempo_at_tick(check_tick);
    // A confirmed tempo step should reach the next unrendered beat even when a minor
    // correction was just published. Small jitter corrections retain the usual spacing.
    let tempo_step = (slope - bpm).abs() >= slope * 0.08;
    let spacing = if s.recovering_tempo_step || s.tempo_ramp { 2 } else { 6 };
    if s.state != State::Locked || s.pulse <= origin || (!tempo_step && since_edit < spacing * TICKS_PER_PULSE) {
        return false;
    }
    let start = grid.tick_to_samples(origin.saturating_mul(TICKS_PER_PULSE), sr);
    let elapsed = sr.samples(s.stamp_us.saturating_sub(stamp) as f64 / 1e6);
    let phase = sr.seconds(start.saturating_add(elapsed).saturating_sub(grid.tick_to_samples(tick, sr)));
    let (bpm_deadband, phase_deadband) = if s.recovering_tempo_step && s.jitter_us > 50. {
        (0.03, 0.001)
    } else if s.tempo_ramp {
        (0.035, 0.0005)
    } else {
        (0.15, 0.003)
    };
    if (slope - bpm).abs() < bpm_deadband && phase.abs() < phase_deadband {
        return false;
    }
    if s.recovering_tempo_step {
        // Join the new wire grid at a future pulse. Only the interval after
        // the committed audio changes; then restore the source's exact tempo.
        let edit_sample = grid.tick_to_samples(edit, sr);
        let elapsed_at_edit = sr.seconds(edit_sample.saturating_sub(start).saturating_sub(elapsed));
        let wire_at_edit = tick as f64 + elapsed_at_edit * bpm * TICKS_PER_QUARTER as f64 / 60.;
        let ahead = (edit as f64).max(wire_at_edit);
        let join = ((ahead / TICKS_PER_PULSE as f64).ceil() as i64).saturating_add(1).saturating_mul(TICKS_PER_PULSE);
        if join <= edit {
            return false;
        }
        let seconds = (join as f64 - wire_at_edit) * 60. / (bpm * TICKS_PER_QUARTER as f64);
        let bridge = (join - edit) as f64 * 60. / (seconds * TICKS_PER_QUARTER as f64);
        if grid.set_tempo(edit, bridge.clamp(5., 1000.)).is_ok() {
            let _ = grid.set_tempo(join, bpm);
            return true;
        }
        return false;
    }
    let recovery_beats = if s.tempo_ramp {
        0.6
    } else if phase.abs() <= 0.006 {
        8.
    } else {
        4.
    };
    let target = bpm / (1. + (phase * bpm / (60. * recovery_beats)).clamp(-0.05, 0.05));
    (slope - target).abs() >= bpm_deadband && grid.set_tempo(edit, target.clamp(5., 1000.)).is_ok()
}


mod sampler_song {
use soundcraft_midi::{Note, Sequence};
use soundcraft_model::{ChannelFormat, Clip, Insert, Session, SourceAudio, SourceId, TrackKind};
use soundcraft_time::{SampleRate, TempoMap};
use std::sync::Arc;

/// An eighth-note pattern playing a known 96-sample burst at its native pitch.
pub(super) fn sampler_song(grid: TempoMap, sr: SampleRate, count: usize, end: i64) -> Session {
    let mut song = Session { tempo: grid, sample_rate: sr, ..Default::default() };
    let source = SourceId(200);
    // A varying waveform reveals duplicated or stretched samples. Keep its envelope
    // above the gate so a single voice has one unambiguous attack and release.
    let burst = (0..96).map(|i| 0.5 + 0.3 * (i as f32 * 0.31).sin()).collect();
    song.pool.insert(source, Arc::new(SourceAudio::new(craft_audio::AudioBuffer { sample_rate: sr.hz(), channels: vec![burst] })));
    let id = song.add_track(TrackKind::Instrument, ChannelFormat::Stereo, None);
    let clip = song.new_clip_id();
    let tr = song.track_mut(id).unwrap();
    let mut inst = Insert::new("sampler");
    inst.sample = Some(source);
    inst.params.insert("root_note".into(), 60.);
    inst.params.insert("attack".into(), 0.);
    tr.instrument = Some(inst);
    let mut seq = Sequence::default();
    for i in 0..count {
        seq.notes.push(Note { start: i as i64 * 480, length: 80, pitch: 60, channel: 0, velocity: 110, release_velocity: 64 });
    }
    tr.playlist_mut().unwrap().clips.push(Clip::midi(clip, "hats", 0, end.saturating_add(i64::from(sr.hz())), seq));
    song
}

}
mod dj_render {
use super::sampler_song::sampler_song;
use super::*;
use soundcraft_model::{ChannelFormat, ClipContent, Session, SourceAudio, SourceId, TrackKind};
use std::sync::{Arc, OnceLock};

const TAGS: usize = 16;
const HAT: usize = 96;
const KICK: usize = 240;
const SCORE_WINDOW: usize = 64;
const ORIGIN: i64 = 20_000;

#[derive(Clone, Copy, Debug)]
pub(super) enum Ending {
    Release,
    Stop,
    Loss { coast: bool },
}

pub(super) struct Rendered {
    /// Every onset recovered from the PCM, grouped by scored eighth; errors in 48 kHz samples.
    pub attacks: Vec<Vec<i64>>,
    pub damaged: usize,
    pub extra: usize,
    pub tail_open: bool,
    pub snapshots: Vec<Snapshot>,
    pub transitions: Vec<(usize, i64, State)>,
    pub final_state: State,
    pub tempo_events: usize,
}

fn band_song(start_bpm: f64, capacity: usize, end: i64) -> Session {
    let sr = SampleRate::HZ_48000;
    let mut song = sampler_song(TempoMap::new(start_bpm, 4, 4).unwrap(), sr, capacity, end);
    let id = song.new_clip_id();
    let mut clip = song.tracks[0].playlist_mut().unwrap().clips[0].clone();
    clip.id = id;
    let mut instrument = song.tracks[0].instrument.clone().unwrap();
    let source = SourceId(201);
    // Short kick with a decaying low-frequency body, distinguishable from the brighter
    // 96-sample hi-hat even when both attacks fall on the same PCM sample.
    let kick = (0..KICK)
        .map(|i| {
            let phase = i as f32 / KICK as f32;
            0.35 * (-4. * phase).exp() * (1. + 0.6 * (phase * 3.8).cos())
        })
        .collect();
    song.pool.insert(source, Arc::new(SourceAudio::new(craft_audio::AudioBuffer { sample_rate: sr.hz(), channels: vec![kick] })));
    instrument.sample = Some(source);
    let track = song.add_track(TrackKind::Instrument, ChannelFormat::Stereo, None);
    let kick = song.track_mut(track).unwrap();
    kick.instrument = Some(instrument);
    kick.playlist_mut().unwrap().clips.push(clip);
    song
}

fn score_window(song: &mut Session, first: usize, total: usize) {
    for (track_index, stride) in [1, 2].into_iter().enumerate() {
        let clip = &mut song.tracks[track_index].playlist_mut().unwrap().clips[0];
        let ClipContent::Midi { sequence } = &mut clip.content else { unreachable!() };
        // first moves forward only. The window starts full and only shrinks for the final section.
        sequence.notes.truncate(total.saturating_sub(first).div_ceil(stride));
        for (i, note) in sequence.notes.iter_mut().enumerate() {
            let eighth = first + i * stride;
            note.start = eighth as i64 * 480;
            note.velocity = 32 + (eighth % TAGS) as u8 * 6;
        }
    }
}

/// Each tag has a distinct velocity and an independently rendered native-pitch waveform.
/// Comparing the entire voice checks its release as well as its attack.
fn templates() -> &'static [Vec<f32>] {
    static REFERENCE: OnceLock<Vec<Vec<f32>>> = OnceLock::new();
    REFERENCE.get_or_init(|| {
        let mut song = band_song(120., TAGS, 192_000);
        score_window(&mut song, 0, TAGS);
        let mut mix = soundcraft_mix::MixEngine::new(48_000., 128);
        let mut output = vec![vec![0.; 128]; 2];
        let mut waves = Vec::<Vec<f32>>::new();
        let mut sounding = false;
        for pos in (0..192_000).step_by(128) {
            mix.render_with_clock_limit(&song, pos, 128, &mut output, None);
            for &value in &output[0] {
                if value.abs() > 0.000001 {
                    if !sounding {
                        waves.push(Vec::with_capacity(KICK));
                    }
                    waves.last_mut().unwrap().push(value);
                    sounding = true;
                } else {
                    sounding = false;
                }
            }
        }
        assert_eq!(waves.len(), TAGS);
        assert!(waves.iter().enumerate().all(|(i, v)| v.len() == if i % 2 == 0 { KICK } else { HAT }));
        assert!(waves.windows(2).all(|pair| pair[0] != pair[1]));
        waves
    })
}

fn put_voice(result: &mut Rendered, expected: &[i64], start: i64, audio: &[f32]) {
    let references = templates();
    let tag = references.iter().position(|v| v == audio).unwrap_or_else(|| {
        result.damaged += 1;
        references.iter().enumerate().min_by(|(_, a), (_, b)| (a[0] - audio[0]).abs().total_cmp(&(b[0] - audio[0]).abs())).unwrap().0
    });
    // The same velocity repeats only after eight beats. Check the neighbouring repeats
    // without scanning an entire long song for every note.
    let nearest = expected.partition_point(|at| *at < start);
    let group = nearest / TAGS;
    let candidates = group.saturating_sub(1)..=group + 1;
    if let Some(i) = candidates.map(|g| g * TAGS + tag).filter(|i| *i < expected.len()).min_by_key(|i| start.abs_diff(expected[*i])) {
        result.attacks[i].push(start - expected[i]);
    } else {
        result.extra += 1;
    }
}

pub(super) fn render_dj(start_bpm: f64, ideal_us: &[i64], arrivals_us: &[i64], ending: Ending) -> Rendered {
    assert_eq!(ideal_us.len(), arrivals_us.len());
    assert!(ideal_us.len() >= 2 && arrivals_us.windows(2).all(|w| w[1] >= w[0]));
    let sr = SampleRate::HZ_48000;
    let sample = |us: i64| sr.samples(us as f64 / 1e6);
    let expected: Vec<_> = ideal_us.iter().step_by(12).map(|us| sample(*us)).collect();
    let mut result = Rendered {
        attacks: vec![vec![]; expected.len()],
        damaged: 0,
        extra: 0,
        tail_open: false,
        snapshots: Vec::with_capacity(ideal_us.len()),
        transitions: vec![],
        final_state: State::Waiting,
        tempo_events: 0,
    };
    let last = *arrivals_us.last().unwrap();
    let stop_at = matches!(ending, Ending::Stop).then_some(last + 20_000);
    let end = last + if matches!(ending, Ending::Loss { .. }) { 2_010_000 } else { 100_000 };
    let inputs = MidiInputs::with_port_names(vec![], vec!["DJ".into()]);
    let feed = inputs.feed();
    let port = feed.ports().assign("DJ");
    feed.set_clock_follow(Some(port), !matches!(ending, Ending::Loss { coast: false }), 0, false);
    feed.set_clock(ORIGIN);
    feed.receive(port, &[0xfa]);
    let mut song = band_song(start_bpm, expected.len().min(SCORE_WINDOW), sample(end));
    let mut mix = soundcraft_mix::MixEngine::new(48_000., 128);
    let mut output = vec![vec![0.; 128]; 2];
    let mut voice = Vec::with_capacity(KICK);
    let mut onset = 0;
    let mut pos = 0;
    let mut now = 0;
    let mut p = 0;
    let mut running = false;
    let mut actions = Vec::new();
    loop {
        feed.set_clock(ORIGIN + now);
        let pulse = arrivals_us.get(p) == Some(&now);
        if pulse {
            // Keep a bounded window of notes in the score, with overlap in both directions.
            // The mix graph, tempo map and follower run uninterrupted for a multi-hour case.
            if p.is_multiple_of(384) {
                score_window(&mut song, (p / 12).saturating_sub(16), expected.len());
            }
            feed.receive(port, &[0xf8]);
        } else if stop_at == Some(now) {
            feed.receive(port, &[0xfc]);
        }
        let snap = feed.clock_follow_status(&mut actions);
        for action in actions.drain(..) {
            match action {
                Action::Stop => {
                    running = false;
                    mix.reset();
                }
                Action::Play { .. } | Action::Started { .. } => running = true,
                Action::Locate(_) => {}
            }
        }
        if snap.state != result.final_state {
            result.transitions.push((p, now, snap.state));
            result.final_state = snap.state;
        }
        if pulse {
            result.snapshots.push(snap);
            update_grid(&mut song.tempo, Some((0, ORIGIN + arrivals_us[0])), 0, snap, sr, pos + 1440);
            p += 1;
        }
        if now >= end {
            break;
        }
        let next_wire = arrivals_us.get(p).copied().unwrap_or(end);
        // A loss must be observable in the silence before the next packet. At ordinary
        // tempos the next F8 arrives well inside the minimum loss timeout.
        let previous = arrivals_us.get(p.saturating_sub(1)).copied().unwrap_or(0);
        let mut next = if next_wire - previous >= 75_000 { next_wire.min(now + 1_000) } else { next_wire };
        if let Some(stop) = stop_at.filter(|s| *s > now) {
            next = next.min(stop);
        }
        let until = sample(next);
        while pos < until {
            let count = (until - pos).min(128) as usize;
            if running {
                mix.render_with_clock_limit(&song, pos, count, &mut output, feed.clock_render_tick());
            }
            for i in 0..count {
                let value = if running { output[0][i] } else { 0. };
                if value.abs() > 0.000001 {
                    if voice.is_empty() {
                        onset = pos + i as i64;
                    }
                    voice.push(value);
                } else if !voice.is_empty() {
                    put_voice(&mut result, &expected, onset, &voice);
                    voice.clear();
                }
            }
            pos += count as i64;
        }
        now = next;
    }
    result.tail_open = !voice.is_empty();
    result.tempo_events = song.tempo.tempos().len();
    result
}

}
mod dj_tempos {
use super::dj_render::{Ending, Rendered, render_dj};

const WARMUP: usize = 384;

fn whole_song(pulses: usize, mut interval_us: impl FnMut(usize, f64) -> f64) -> Vec<i64> {
    let mut at = 0.0_f64;
    (0..=pulses)
        .map(|p| {
            let stamp = at.round() as i64;
            at += interval_us(p, at);
            stamp
        })
        .collect()
}

fn jitter(ideal: &[i64], amplitude: i64, mut seed: u64) -> Vec<i64> {
    ideal
        .iter()
        .enumerate()
        .map(|(p, at)| {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            if p == 0 { *at } else { *at + ((seed >> 32) % (2 * amplitude + 1) as u64) as i64 - amplitude }
        })
        .collect()
}

fn period(bpm: f64) -> f64 {
    2_500_000. / bpm
}

fn errors(name: &str, r: &Rendered) -> Vec<i64> {
    assert_eq!(r.extra, 0, "{name}: unmatched attack");
    assert!(!r.tail_open, "{name}: sound past the fixture release");
    assert_eq!(r.damaged, 0, "{name}: incomplete or changed waveform");
    let signed: Vec<_> = r
        .attacks
        .iter()
        .enumerate()
        .map(|(i, note)| {
            assert_eq!(note.len(), 1, "{name}: eighth {i}, offsets {note:?}");
            note[0]
        })
        .collect();
    eprintln!("{name} signed eighth errors (48 kHz samples) {signed:?}");
    signed
}

fn peak(samples: &[i64]) -> i64 {
    samples.iter().map(|v| v.abs()).max().unwrap_or(0)
}

fn steps(r: &Rendered) -> Vec<usize> {
    r.snapshots.iter().enumerate().filter(|(_, s)| s.step_intervals != 0).map(|(p, _)| p).collect()
}

#[test]
fn small_dj_nudges_keep_each_eighth_and_settle_in_two_beats() {
    for amplitude in [0, 1000] {
        for pct in [-5., -3.5, -2., 2., 3.5, 5.] {
            for duration in [500_000., 1_000_000., 2_000_000.] {
                let start = WARMUP as f64 * period(128.);
                let release = start + duration;
                let bpm = 128. * (1. + pct / 100.);
                let ideal = whole_song(WARMUP + 288, |p, at| {
                    if p < WARMUP || at >= release {
                        return period(128.);
                    }
                    // A nudge ends at the specified time, even between two wire pulses.
                    let left = release - at;
                    if left >= period(bpm) { period(bpm) } else { left + period(128.) * (1. - left / period(bpm)) }
                });
                let r = render_dj(128., &ideal, &jitter(&ideal, amplitude, 42), Ending::Release);
                let name = format!("nudge {pct}% {duration}us jitter {amplitude}us");
                let signed = errors(&name, &r);
                assert!(steps(&r).is_empty(), "{name} false steps {:?}", steps(&r));
                let deadline = ideal.partition_point(|&t| (t as f64) < release) + 48;
                let settle = r.snapshots[deadline].bpm.unwrap();
                assert!((settle - 128.).abs() <= 0.1, "{name}: {settle} BPM");
                assert!(peak(&signed[WARMUP / 12..]) <= 192, "{name}: peak {} samples", peak(&signed[WARMUP / 12..]));
            }
        }
    }
}

#[test]
fn half_and_double_time_keep_the_first_offbeat_and_following_eighths() {
    for amplitude in [0, 1000] {
        for (from, to) in [(174., 87.), (87., 174.), (140., 70.), (70., 140.), (120., 60.), (60., 120.)] {
            for cut in [WARMUP, WARMUP + 12] {
                let ideal = whole_song(cut + 192, |p, _| period(if p < cut { from } else { to }));
                let r = render_dj(from, &ideal, &jitter(&ideal, amplitude, 42), Ending::Release);
                let name = format!("ratio {from}->{to} at {cut} jitter {amplitude}us");
                let signed = errors(&name, &r);
                let x = &signed[cut / 12..];
                assert!(x[0].abs() <= 192 && x[1].abs() <= 480 && peak(&x[2..]) <= 192, "{name}");
            }
        }
    }
}

#[test]
fn exact_step_threshold_uses_pretransition_period_in_both_directions() {
    for amplitude in [0, 1000] {
        for pct in [-8.1_f64, -8.0, -7.9, 7.9, 8.0, 8.1] {
            for trial in 0..10 {
                let cut = WARMUP + trial;
                let ideal = whole_song(cut + 192, |p, _| period(if p < cut { 128. } else { 128. * (1. + pct / 100.) }));
                let r = render_dj(128., &ideal, &jitter(&ideal, amplitude, 42 + trial as u64), Ending::Release);
                let name = format!("threshold {pct} trial {trial} jitter {amplitude}us");
                let signed = errors(&name, &r);
                let transitions = steps(&r);
                eprintln!("{name}: confirmed at {transitions:?}, cut {cut}");
                if pct.abs() < 8. {
                    assert!(transitions.is_empty(), "{name}: false steps {transitions:?}");
                    assert!(peak(&signed[cut.div_ceil(12)..]) <= 192, "{name}");
                } else {
                    assert!(matches!(transitions.as_slice(), [p] if *p > cut), "{name}: {transitions:?}");
                }
            }
        }
    }
}

#[test]
fn accelerating_build_detects_the_drop_on_a_linear_and_convex_ramp() {
    let length = 8 * 4 * 24;
    let drop = WARMUP + length;
    for convex in [false, true] {
        for amplitude in [0, 1000] {
            let ideal = whole_song(drop + 192, |p, _| {
                if !(WARMUP..drop).contains(&p) {
                    return period(128.);
                }
                let x = (p - WARMUP) as f64 / length as f64;
                let y = x + 1. / length as f64;
                // Integrate one wire interval against BPM as a function of score position.
                if convex {
                    let scale = (32_f64 / 128.).sqrt();
                    2_500_000. * length as f64 / (128_f64 * 32.).sqrt() * ((y * scale).atan() - (x * scale).atan())
                } else {
                    2_500_000. * length as f64 / 32. * ((128. + 32. * y) / (128. + 32. * x)).ln()
                }
            });
            let r = render_dj(128., &ideal, &jitter(&ideal, amplitude, 42), Ending::Release);
            let name = format!("build convex={convex} jitter={amplitude}");
            let s = errors(&name, &r);
            let det = steps(&r);
            assert!(matches!(det.as_slice(),[p] if *p>drop), "{name} step pulses {det:?}");
            assert!(peak(&s[WARMUP / 12..=drop / 12]) <= 192, "{name} ramp");
            assert!(s[drop / 12 + 1].abs() <= 480 && peak(&s[drop / 12 + 2..]) <= 192, "{name} drop");
        }
    }
}

#[test]
fn gradual_one_percent_steps_follow_the_grid_without_confirming_a_large_step() {
    let mut levels = vec![120_f64];
    while *levels.last().unwrap() < 132. {
        levels.push((levels.last().unwrap() * 1.01).min(132.));
    }
    while *levels.last().unwrap() > 120. {
        levels.push((levels.last().unwrap() * 0.99).max(120.));
    }
    let ideal = whole_song(WARMUP + 24 * levels.len() + 192, |p, _| {
        let i = if p < WARMUP { 0 } else { ((p - WARMUP) / 24 + 1).min(levels.len() - 1) };
        period(levels[i])
    });
    for amplitude in [0, 1000] {
        let r = render_dj(120., &ideal, &jitter(&ideal, amplitude, 42), Ending::Release);
        let s = errors("one-percent tempo staircase", &r);
        assert!(steps(&r).is_empty());
        assert!(peak(&s[WARMUP / 12..]) <= 192, "jitter {amplitude}: {} samples", peak(&s[WARMUP / 12..]));
    }
}

#[test]
fn sinusoidal_tempo_wobble_keeps_each_eighth_without_false_steps() {
    for depth in [0.005, 0.01] {
        for frequency in [0.5, 2.] {
            let omega = std::f64::consts::TAU * frequency;
            let origin = WARMUP as f64 * period(128.);
            let ideal = whole_song(WARMUP + 64 * 4 * 24, |p, at| {
                if p < WARMUP {
                    return period(128.);
                }
                let t = (at - origin) / 1e6;
                // Invert the exact integral of the sinusoid over this pulse.
                let (mut lo, mut hi) = (0., 0.04);
                for _ in 0..40 {
                    let mid = (lo + hi) * 0.5;
                    let phase = 128. * (mid + depth * ((omega * t).cos() - (omega * (t + mid)).cos()) / omega);
                    if phase < 2.5 {
                        lo = mid;
                    } else {
                        hi = mid;
                    }
                }
                (lo + hi) * 0.5e6
            });
            for amplitude in [0, 1000] {
                let r = render_dj(128., &ideal, &jitter(&ideal, amplitude, 42), Ending::Release);
                let name = format!("wobble {depth} {frequency}Hz jitter {amplitude}");
                let s = errors(&name, &r);
                let toggles = r.snapshots.windows(2).filter(|p| p[0].tempo_ramp != p[1].tempo_ramp).count();
                eprintln!("{name}: ramp toggles {toggles}");
                assert!(steps(&r).is_empty(), "{name}");
                assert!(peak(&s[WARMUP / 12..]) <= 192, "{name}");
            }
        }
    }
}
#[test]
#[ignore = "20 five-to-seven-minute tracks at 48 kHz; run serially"]
fn twenty_full_length_dj_tracks_preserve_the_recorded_eighths_through_transitions() {
    let bpms = [118., 124., 130., 136., 142., 148., 142., 136., 130., 124., 118., 124., 130., 136., 142., 148., 142., 136., 130., 124.];
    let mut ideal = Vec::new();
    let mut exclude = Vec::new();
    let mut burst = 0..0;
    let mut time = 0_f64;
    for (track, &tempo) in bpms.iter().enumerate() {
        let seconds = 303. + ((track * 37) % 101) as f64;
        let bars = (seconds * tempo / 240.).ceil() as usize;
        let length = bars * 96;
        let start = ideal.len();
        let blend = length - 16 * 96;
        let next = bpms.get(track + 1).copied().unwrap_or(tempo);
        let special = 32 * 96;
        for p in 0..length {
            let bpm = if track == 7 && (special..special + 48).contains(&p) {
                let k = p - special;
                if k < 24 { tempo * (5_f64 / tempo).powf((k + 1) as f64 / 24.) } else { 5. * (tempo / 5.).powf((k - 23) as f64 / 24.) }
            } else if track == 12 && (special..special + 16 * 96).contains(&p) {
                tempo / 2.
            } else if p >= blend {
                tempo + (next - tempo) * (p - blend) as f64 / (length - blend) as f64
            } else {
                tempo
            };
            ideal.push(time.round() as i64);
            if ideal.len() % 12 == 1 {
                let pickup = track == 0 && p < 48;
                let mixing = track + 1 < bpms.len() && p >= blend;
                let braking = track == 7 && (special..special + 96).contains(&p);
                let half_step = track == 12 && ((special..special + 48).contains(&p) || (special + 16 * 96..special + 16 * 96 + 48).contains(&p));
                exclude.push(pickup || mixing || braking || half_step);
            }
            time += period(bpm);
        }
        if track == 5 {
            burst = start + special..start + special + 16 * 96;
        }
    }
    let mut arrived = jitter(&ideal, 1000, 71);
    let mut head = burst.start;
    let mut width = 3;
    while head < burst.end {
        let end = (head + width).min(burst.end);
        let last = arrived[end - 1];
        for (i, t) in arrived[head..end].iter_mut().enumerate() {
            *t = last + i as i64 * 200;
        }
        width = if width == 5 { 3 } else { width + 1 };
        head = end;
    }
    let r = render_dj(bpms[0], &ideal, &arrived, Ending::Release);
    let signed = errors("20 tracks; 16-bar blends; seeded jitter; brake, half-time and causal bursts", &r);
    assert_eq!(signed.len(), exclude.len());
    let mut stable: Vec<_> = signed.iter().zip(&exclude).filter(|(_, skip)| !**skip).map(|(x, _)| x.abs()).collect();
    stable.sort_unstable();
    let p999 = stable[(stable.len() * 999).div_ceil(1000) - 1];
    eprintln!("20 tracks, {} eighths, {} outside transitions, p99.9 {p999} samples, {} grid events", signed.len(), stable.len(), r.tempo_events);
    assert!(p999 <= 192);
}

}
mod brake {
use super::dj_render::{Ending, render_dj};
use super::*;

fn jitter(stamps: &[i64], amplitude: i64) -> Vec<i64> {
    let mut seed = 341_u64;
    stamps
        .iter()
        .enumerate()
        .map(|(index, &at)| {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            at + if index == 0 { 0 } else { ((seed >> 32) % (2 * amplitude + 1) as u64) as i64 - amplitude }
        })
        .collect()
}

#[test]
fn brake_steady_slow_sources_lock_from_start_without_losing_notes() {
    let mut failures = Vec::new();
    for bpm in [16., 10., 5.] {
        let ideal: Vec<_> = (0..49).map(|p| (p as f64 * 2_500_000.0 / bpm).round() as i64).collect();
        for noise in [0, 1000] {
            let wire = jitter(&ideal, noise);
            let r = render_dj(bpm, &ideal, &wire, Ending::Release);
            let last = r.snapshots.last().unwrap();
            eprintln!(
                "steady {bpm} BPM jitter {noise}: eighth sample errors {:?}; transitions {:?}; losses {}, damage {}, extras {}, open tail {}",
                r.attacks, r.transitions, last.dropouts, r.damaged, r.extra, r.tail_open
            );
            if last.state != State::Locked
                || last.dropouts != 0
                || last.bpm.is_none_or(|v| (v - bpm).abs() > 0.01)
                || r.attacks.iter().any(|a| a.len() != 1)
                || r.damaged != 0
                || r.extra != 0
                || r.tail_open
            {
                failures.push((bpm, noise));
            }
        }
    }
    assert!(failures.is_empty(), "slow source(s) failed: {failures:?}");
}

#[test]
fn brake_shapes_keep_the_wire_phase_and_obey_each_ending() {
    const CUT: usize = 192;
    let mut failures = Vec::new();
    for length in [24, 48] {
        for exponential in [false, true] {
            for noise in [0, 1000] {
                for ending in [Ending::Stop, Ending::Loss { coast: true }, Ending::Loss { coast: false }, Ending::Release] {
                    let rise = matches!(ending, Ending::Release);
                    let base = CUT + length + 24; // Sustain five BPM for a full beat.
                    let pulses = base + if rise { 24 + 96 } else { 0 };
                    let mut time = 0.0_f64;
                    let ideal: Vec<_> = (0..=pulses)
                        .map(|p| {
                            let t = time.round() as i64;
                            let bpm = if p < CUT {
                                128.
                            } else if p < CUT + length {
                                let phase = (p - CUT + 1) as f64 / length as f64;
                                if exponential { 128. * (5.0_f64 / 128.).powf(phase) } else { 128. - 123. * phase }
                            } else if p < base {
                                5.
                            } else {
                                5. + 123. * ((p - base + 1) as f64 / 24.).min(1.)
                            };
                            time += 2_500_000. / bpm;
                            t
                        })
                        .collect();
                    let wire = jitter(&ideal, noise);
                    let r = render_dj(128., &ideal, &wire, ending);
                    let snap = r.snapshots.last().unwrap();
                    let mut ok = r.snapshots.iter().all(|s| s.state == State::Locked && s.dropouts == 0)
                        && r.damaged == 0
                        && r.extra == 0
                        && !r.tail_open
                        && r.attacks.iter().all(|v| v.len() == 1);
                    let min_wire_error = (CUT / 12 + 1..=base / 12)
                        .flat_map(|e| {
                            let delay = (wire[e * 12] - ideal[e * 12]) as f64 * 0.048;
                            r.attacks[e].iter().map(move |offset| *offset as f64 - delay)
                        })
                        .fold(0.0_f64, f64::min);
                    ok &= min_wire_error >= -48. && r.snapshots[base].bpm.is_some_and(|b| (5. - b).abs() < 0.1);
                    if rise {
                        ok &= snap.bpm.is_some_and(|v| (v - 128.).abs() < 0.1)
                            && r.attacks[(base + 24) / 12..].iter().flatten().all(|e| e.abs() <= 192);
                    } else {
                        ok &= r.final_state == if matches!(ending, Ending::Loss { coast: true }) { State::Coasting } else { State::Stopped };
                    }
                    let transitions: Vec<_> = r
                        .transitions
                        .iter()
                        .map(|&(p, t, state)| {
                            let prev = wire.get(p.saturating_sub(1)).copied().unwrap_or(0);
                            (p, t, state, t - prev)
                        })
                        .collect();
                    eprintln!(
                        "brake {length} exponential={exponential} jitter={noise} {ending:?}: eighth errors {:?}; state transitions (pulse, time_us, state, gap_us) {transitions:?}; earliest vs wire {min_wire_error:.1} samples, damage {}, extras {}, open tail {}, at 5 BPM {:?}",
                        r.attacks, r.damaged, r.extra, r.tail_open, r.snapshots[base].bpm
                    );
                    if !ok {
                        failures.push((length, exponential, noise, ending));
                    }
                }
            }
        }
    }
    assert!(failures.is_empty(), "brake failures: {failures:?}");
}

#[test]
fn brake_cable_loss_and_slow_relock_use_clock_and_active_sensing_separately() {
    let inputs = MidiInputs::with_port_names(vec![], vec!["slow master".into()]);
    let feed = inputs.feed();
    let port = feed.ports().assign("slow master");
    feed.set_clock_follow(Some(port), true, 0, false);
    let send = |time, status| {
        feed.set_clock(time);
        feed.receive(port, &[status]);
    };
    let status = |time| {
        feed.set_clock(time);
        feed.clock_follow_status(&mut Vec::new())
    };
    send(0, 0xfa);
    for p in 0..=24 {
        send(p * 20_000, 0xf8);
    }
    let last = 24 * 20_000;
    assert_eq!(status(last + 150_000).state, State::Locked);
    assert_eq!(status(last + 150_001).state, State::Coasting);
    let at = last + 300_000;
    send(at, 0xf8);
    assert_eq!(status(at + 249_999).state, State::Coasting);
    send(at + 250_000, 0xf8);
    let relocked = status(at + 250_000);
    assert_eq!(relocked.state, State::Locked, "the second 10 BPM pulse relocks");
    assert!((relocked.bpm.unwrap() - 10.).abs() < 0.01);

    send(at + 250_100, 0xfe);
    send(at + 450_100, 0xfe);
    assert_eq!(status(at + 749_999).state, State::Locked);
    assert_eq!(status(at + 750_101).state, State::Coasting, "a source that enabled Active Sensing stopped sending MIDI for 300 ms");
}

#[test]
fn active_sensing_counts_channel_messages_from_its_own_port_as_presence() {
    let inputs = MidiInputs::with_port_names(vec![], vec!["clock".into(), "other".into()]);
    let feed = inputs.feed();
    let master = feed.ports().assign("clock");
    let other = feed.ports().assign("other");
    feed.set_clock_follow(Some(master), true, 0, false);
    feed.set_clock(0);
    feed.receive(master, &[0xfa, 0xf8]);
    for p in 1..=24 {
        feed.set_clock(p * 140_000);
        feed.receive(master, &[0xf8]);
    }
    let last = 24 * 140_000;
    feed.set_clock(last + 5_000);
    feed.receive(master, &[0xfe]);
    feed.set_clock(last + 30_000);
    feed.receive(master, &[0x90, 60, 100]);
    feed.set_clock(last + 300_000);
    feed.receive(other, &[0xfe]);
    feed.set_clock(last + 330_000);
    assert_eq!(feed.clock_follow_status(&mut Vec::new()).state, State::Locked);
    feed.set_clock(last + 330_001);
    assert_eq!(feed.clock_follow_status(&mut Vec::new()).state, State::Coasting);
}

}
mod packet_steps {
use super::sampler_song::sampler_song;
use super::*;

#[derive(Debug, Clone, Copy)]
enum Delivery {
    Jitter(i64),
    Burst(usize),
    VariableBurst,
}
fn delivery_times(ideal: &[f64], mode: Delivery) -> Vec<i64> {
    let mut seed = 42u64;
    let mut times = Vec::with_capacity(ideal.len());
    let mut group = 0;
    while times.len() < ideal.len() {
        let p = times.len();
        match mode {
            Delivery::Jitter(amplitude) => {
                seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                let delta = ((seed >> 32) % (2 * amplitude + 1) as u64) as i64 - amplitude;
                times.push(ideal[p].round() as i64 + if p == 0 { 0 } else { delta });
            }
            _ => {
                let n = if let Delivery::Burst(n) = mode { n } else { 3 + group % 3 };
                // The first clock starts the audio transport. Deliver the initial group
                // individually so the sampler and clock share the same transport origin.
                let width = n.min(ideal.len() - p);
                if p == 0 {
                    times.extend(ideal.iter().take(width).map(|at| at.round() as i64));
                } else {
                    // A coalesced group can only arrive after its last pulse was sent.
                    let last = ideal[p + width - 1].round() as i64;
                    for j in 0..width {
                        times.push(last + j as i64 * 200);
                    }
                }
                group += 1;
            }
        }
    }
    times
}
struct Observation {
    attacks: Vec<Vec<i64>>,
    // Physical lateness of the event's own F8, independent of SoundCraft.
    wire: Vec<i64>,
    malformed: usize,
    unmatched: usize,
    steps: Vec<(usize, u8)>,
    dropouts: u64,
}
fn render_train(from: f64, to: f64, transition: usize, n: usize, mode: Delivery) -> Observation {
    let sr = SampleRate::HZ_48000;
    let inputs = MidiInputs::with_port_names(vec![], vec!["source".into()]);
    let feed = inputs.feed();
    let port = feed.ports().assign("source");
    feed.set_clock_follow(Some(port), true, 0, false);
    feed.set_clock(0);
    feed.receive(port, &[0xfa]);
    let mut now = 0.;
    let ideal: Vec<f64> = (0..n)
        .map(|p| {
            let t = now;
            now += 2_500_000. / if p < transition { from } else { to };
            t
        })
        .collect();
    let times = delivery_times(&ideal, mode);
    let expected: Vec<_> = ideal.iter().step_by(12).map(|at| sr.samples(at / 1e6)).collect();
    let end = sr.samples(now / 1e6) + 48_000;
    let mut song = sampler_song(TempoMap::new(from, 4, 4).unwrap(), sr, expected.len(), end);
    let mut mixer = soundcraft_mix::MixEngine::new(48_000., 512);
    let mut block = vec![vec![0.; 512]; 2];
    let mut pos = 0;
    let mut steps = Vec::new();
    let mut actions = Vec::new();
    let mut dropouts = 0;
    let mut hits: Vec<(i64, Vec<f32>)> = Vec::new();
    let mut sounding = false;
    for p in 0..=n {
        let until = times.get(p).map_or(end, |at| sr.samples(*at as f64 / 1e6));
        while pos < until {
            let frames = (until - pos).min(512) as usize;
            mixer.render_with_clock_limit(&song, pos, frames, &mut block, feed.clock_render_tick());
            for (i, &v) in block[0][..frames].iter().enumerate() {
                let high = v.abs() > 0.001;
                if high {
                    if !sounding {
                        hits.push((pos + i as i64, Vec::with_capacity(96)));
                    }
                    hits.last_mut().unwrap().1.push(v);
                }
                sounding = high;
            }
            pos += frames as i64;
        }
        if p < n {
            feed.set_clock(times[p]);
            feed.receive(port, &[0xf8]);
            let snap = feed.clock_follow_status(&mut actions);
            actions.clear();
            if snap.step_intervals != 0 {
                steps.push((p, snap.step_intervals));
            }
            dropouts = snap.dropouts;
            update_grid(&mut song.tempo, Some((0, 0)), 0, snap, sr, pos + 1440);
        }
    }
    let reference = hits.iter().find(|(_, voice)| voice.len() == 96).unwrap();
    let malformed = hits.iter().filter(|(_, voice)| voice != &reference.1).count() + usize::from(sounding);
    let mut attacks = vec![Vec::new(); expected.len()];
    let mut unmatched = 0;
    for (hit, _) in hits {
        let right = expected.partition_point(|v| *v < hit);
        let near = match right {
            0 => 0,
            r if r == expected.len() => r - 1,
            r if hit - expected[r - 1] < expected[r] - hit => r - 1,
            r => r,
        };
        let late = hit - expected[near];
        if near + 1 == expected.len() && late > (expected[near] - expected[near - 1]) / 2 {
            unmatched += 1;
        } else {
            attacks[near].push(late);
        }
    }
    let wire = times.iter().step_by(12).zip(&expected).map(|(time, ideal)| (sr.samples(*time as f64 / 1e6) - ideal).max(0)).collect();
    Observation { attacks, wire, unmatched, malformed, steps, dropouts }
}
fn record(label: &str, r: &Observation, change: usize) {
    let pre = r.steps.iter().filter(|(p, _)| *p <= change).count();
    let onset = r.steps.iter().find(|(p, _)| *p > change).map(|(p, n)| (p - change, n));
    let missing = r.attacks.iter().filter(|v| v.is_empty()).count();
    let extra = r.attacks.iter().map(|v| v.len().saturating_sub(1)).sum::<usize>() + r.unmatched;
    eprintln!(
        "CASE {label} missing={missing} extra={extra} damaged={} dropouts={} early_steps={pre} confirmations={} first={onset:?}",
        r.malformed,
        r.dropouts,
        r.steps.len()
    );
    if std::env::var_os("SOUNDCRAFT_PACKET_TRACE").is_some() {
        eprintln!("HITS {label} {:?}", r.attacks);
        eprintln!("STEPS {label} {:?}", r.steps);
    }
}
#[test]
fn tempo_steps_with_timestamp_noise_render_complete_eighth_notes() {
    let mut valid = true;
    for (from, to) in [(130., 80.), (120., 100.), (180., 60.), (100., 120.), (80., 130.), (60., 180.)] {
        for transition in [384, 396] {
            for mode in [Delivery::Jitter(1000), Delivery::Jitter(2000), Delivery::VariableBurst] {
                let r = render_train(from, to, transition, transition + 193, mode);
                record(&format!("{from}-{to}-{transition}-{mode:?}"), &r, transition);
                if let Delivery::Jitter(_) = mode {
                    // Uniform timestamp noise still gives one observation per wire pulse.
                    let start = transition / 12;
                    valid &= r.attacks[start + 1].iter().all(|x| x.abs() <= 480) // 10 ms
                        && r.attacks[start + 2..].iter().flatten().all(|x| x.abs() <= 288); // 6 ms
                }
                valid &= r.malformed == 0
                    && r.unmatched == 0
                    && r.attacks.iter().all(|v| v.len() == 1)
                    && r.dropouts == 0
                    && matches!(r.steps.as_slice(), [(p, _)] if *p > transition && *p <= transition + 16);
            }
        }
    }
    assert!(valid);
}
#[test]
fn trailing_packed_slowdowns_preserve_every_attack_at_its_wire_time() {
    // 48 kHz. The source has eight beats after the cut, including attacks falling
    // at different positions within each USB batch.
    let verbose = std::env::var_os("SOUNDCRAFT_PACKET_TRACE").is_some();
    let mut valid = true;
    for (from, to) in [(180., 60.), (130., 80.)] {
        for change in [384, 396] {
            for mode in [Delivery::Burst(3), Delivery::Burst(4), Delivery::Burst(5), Delivery::VariableBurst] {
                let r = render_train(from, to, change, change + 193, mode);
                let label = format!("{from}-{to}-{change}-{mode:?}");
                record(&label, &r, change);
                valid &= r.dropouts == 0 && r.unmatched == 0 && r.malformed == 0 && r.attacks.iter().all(|note| note.len() == 1);
                let first_offbeat = (change / 12 + 1) | 1;
                let mut max_wire = 0;
                let mut max_residual = 0;
                let mut worst_early = 0;
                for (k, (notes, &wire)) in r.attacks.iter().zip(&r.wire).enumerate().skip(change / 12 + 1) {
                    let [measured] = notes.as_slice() else { continue };
                    let residual = measured - wire;
                    if verbose {
                        eprintln!("PACKED_NOTE {label} eighth={k} wire_samples={wire} measured_samples={measured} residual_samples={residual}");
                    }
                    max_wire = max_wire.max(wire);
                    max_residual = max_residual.max(residual.abs());
                    worst_early = worst_early.min(*measured);
                    valid &= *measured >= -48 && residual.abs() <= if k == first_offbeat { 480 } else { 288 };
                }
                eprintln!("PACKED {label} max_wire_samples={max_wire} max_residual_samples={max_residual} earliest_samples={worst_early}");
            }
        }
    }
    assert!(valid, "a packed slowdown lost or damaged a voice, or exceeded the attack or wire-relative tolerance");
}

#[test]
#[ignore = "ten simulated minutes for each burst width"]
fn ten_minutes_of_coalesced_delivery_do_not_confirm_a_tempo_step() {
    let mut valid = true;
    for (name, mode) in [("3", Delivery::Burst(3)), ("4", Delivery::Burst(4)), ("5", Delivery::Burst(5)), ("3to5", Delivery::VariableBurst)] {
        let r = render_train(120., 120., 28_800, 28_800, mode);
        record(&format!("A4-{name}"), &r, 28_800);
        valid &= r.steps.is_empty()
            && r.dropouts == 0
            && r.malformed == 0
            && r.unmatched == 0
            && r.attacks.iter().zip(&r.wire).all(|(v, wire)| matches!(v.as_slice(), [x] if (x-wire).abs() <= 1));
    }
    assert!(valid);
}

}