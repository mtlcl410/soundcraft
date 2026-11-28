use super::db_to_gain;
use soundcraft_model::Session;
use soundcraft_time::Samples;

/// Blip length in seconds.
const LEN_S: f64 = 0.03;

/// The click's sound as `setup.click_countoff` sets it: level, and pitch and velocity of the
/// accented (beat 1) and other beats. The metronome and the count-off both play it.
struct Voice {
    gain: f64,
    accent: (f64, f64),
    normal: (f64, f64),
    rate: f64,
    len: i64,
}

impl Voice {
    fn of(s: &Session) -> Voice {
        let rate = s.sample_rate.as_f64();
        Voice {
            gain: f64::from(db_to_gain(s.edit.value("click.volume_db", -6.0).clamp(-60.0, 12.0) as f32)),
            accent: (note_hz(s.edit.value("click.accent_note", 84.0)), s.edit.value("click.accent_velocity", 127.0)),
            normal: (note_hz(s.edit.value("click.normal_note", 72.0)), s.edit.value("click.normal_velocity", 100.0)),
            rate,
            len: (LEN_S * rate) as i64,
        }
    }

    /// Sound the beat that starts `rel` frames into the block (negative: it began earlier).
    fn beat(&self, main: &mut [Vec<f32>], rel: i64, frames: usize, accented: bool) {
        let (hz, vel) = if accented { self.accent } else { self.normal };
        let amp = self.gain * (vel.clamp(1.0, 127.0) / 127.0);
        blip(main, rel, frames, hz, amp as f32, self.rate);
    }
}

/// The metronome on the tempo map: one click per beat, accented on beat 1 of each bar.
pub fn render(s: &Session, pos: Samples, frames: usize, main: &mut [Vec<f32>]) {
    let sr = s.sample_rate;
    let voice = Voice::of(s);
    let len = voice.len;
    let end = pos.saturating_add(frames as i64);
    // Start one blip length early so a click that began in an earlier block still rings into this one.
    let t0 = s.tempo.samples_to_ticks(pos.saturating_sub(len), sr).max(0).saturating_sub(1);
    let mut tick = t0.saturating_sub(s.tempo.bar_beat_at_tick(t0).tick);
    // Blocks hold a few beats at most; the guard only protects against a malformed tempo map.
    for _ in 0..4096 {
        let at = s.tempo.tick_to_samples(tick, sr);
        if at >= end {
            break;
        }
        if at.saturating_add(len) > pos {
            voice.beat(main, at - pos, frames, s.tempo.bar_beat_at_tick(tick).beat == 1);
        }
        tick = tick.saturating_add(s.tempo.meter_at_tick(tick).ticks_per_beat());
    }
}

/// A count-off (Options › Count Off, Pro Tools Reference Guide p. 767): `bars` bars of click
/// before the transport starts, in the meter and at the tempo in force where it starts. The
/// transport stands still meanwhile, so the beats are counted from the start of the count-off,
/// not read from the timeline (which may start at 0).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CountOff {
    /// Bars counted off.
    pub bars: u32,
    /// Beats per bar: the meter's numerator (7 in 7/8).
    pub beats_per_bar: u32,
    /// Length of one beat in session frames: the meter's beat unit at the tempo there.
    pub beat: f64,
}

impl CountOff {
    /// `bars` bars (at least 1) in the meter and at the tempo in force at `at`.
    pub fn at(s: &Session, at: Samples, bars: u32) -> CountOff {
        let tick = s.tempo.samples_to_ticks(at.max(0), s.sample_rate);
        let meter = s.tempo.meter_at_tick(tick);
        let bpm = s.tempo.tempo_at_tick(tick);
        let bpm = if bpm.is_finite() && bpm > 0.0 { bpm } else { 120.0 };
        let per_quarter = s.sample_rate.as_f64() * 60.0 / bpm;
        let quarters = meter.ticks_per_beat() as f64 / soundcraft_time::TICKS_PER_QUARTER as f64;
        CountOff { bars: bars.max(1), beats_per_bar: meter.numerator.max(1), beat: per_quarter * quarters }
    }

    /// Beats in the whole count-off.
    pub fn beats(&self) -> u32 {
        self.bars.saturating_mul(self.beats_per_bar)
    }

    /// Where beat `k` (0-based) starts, in frames from the start of the count-off.
    pub fn beat_at(&self, k: u32) -> Samples {
        (f64::from(k) * self.beat).round() as Samples
    }

    /// Its length in session frames: the transport starts this long after the count-off began.
    pub fn length(&self) -> Samples {
        self.beat_at(self.beats())
    }

    /// The bar (1-based) being counted `elapsed` frames into the count-off.
    pub fn bar_at(&self, elapsed: Samples) -> u32 {
        let beat = if self.beat > 0.0 { (elapsed.max(0) as f64 / self.beat) as u32 } else { 0 };
        (beat / self.beats_per_bar.max(1) + 1).min(self.bars)
    }
}

/// The count-off's clicks for the block that starts `elapsed` frames into it: the metronome's
/// own voice, one click per beat, accented on the first beat of each bar.
pub fn render_countoff(s: &Session, c: &CountOff, elapsed: Samples, frames: usize, main: &mut [Vec<f32>]) {
    let voice = Voice::of(s);
    let end = elapsed.saturating_add(frames as i64);
    for k in 0..c.beats() {
        let at = c.beat_at(k);
        if at >= end {
            break;
        }
        if at.saturating_add(voice.len) > elapsed {
            voice.beat(main, at - elapsed, frames, k % c.beats_per_bar.max(1) == 0);
        }
    }
}

/// Adds one decaying sine blip whose first sample sits `rel` frames into the block (negative
/// when it began before the block) to every channel.
fn blip(main: &mut [Vec<f32>], rel: i64, frames: usize, hz: f64, amp: f32, rate: f64) {
    let len = (LEN_S * rate) as usize;
    let w = std::f64::consts::TAU * hz / rate;
    let first = usize::try_from(-rel).unwrap_or(0);
    for i in first..len {
        let Ok(at) = usize::try_from(rel + i as i64) else { continue };
        if at >= frames {
            break;
        }
        let env = (-6.0 * i as f64 / len as f64).exp() as f32;
        let v = ((w * i as f64).sin() as f32) * env * amp;
        for ch in main.iter_mut() {
            if let Some(d) = ch.get_mut(at) {
                *d += v;
            }
        }
    }
}

/// Click pitch for a MIDI note setting (clamped to the MIDI range).
fn note_hz(note: f64) -> f64 {
    soundcraft_dsp::midi_to_hz(note.clamp(0.0, 127.0))
}
