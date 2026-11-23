#![allow(dead_code,private_interfaces)]
pub struct PulseFit<const N: usize> {
    points: [(i64, i64); N],
    cursor: usize,
    len: usize,
    last: Option<(i64, i64)>,
    slope: f64,
    intercept: f64,
    jitter: f64,
}

impl<const N: usize> Default for PulseFit<N> {
    fn default() -> Self {
        Self { points: [(0, 0); N], cursor: 0, len: 0, last: None, slope: 0., intercept: 0., jitter: 0. }
    }
}

impl<const N: usize> PulseFit<N> {
    pub fn clear(&mut self) {
        self.len = 0;
        self.cursor = 0;
        self.last = None;
        self.slope = 0.;
        self.jitter = 0.;
    }
    pub fn push(&mut self, pulse: i64, at_us: i64) {
        if N == 0 {
            return;
        }
        if self.last.is_some_and(|(i, t)| pulse <= i || at_us < t) {
            self.clear();
        }
        self.points[self.cursor] = (pulse, at_us);
        self.cursor = (self.cursor + 1) % N;
        self.len = (self.len + 1).min(N);
        self.last = Some((pulse, at_us));
        if self.len < 2 {
            return;
        }
        // Centre relative to the newest stamp; a long host uptime cannot
        // lose short timestamp differences in large sum-of-squares terms.
        let n = self.len as f64;
        let mut x = 0.;
        let mut y = 0.;
        let mut xx = 0.;
        let mut xy = 0.;
        let mut yy = 0.;
        for &(i, t) in &self.points[..self.len] {
            let dx = i.saturating_sub(pulse) as f64;
            let dy = t.saturating_sub(at_us) as f64;
            x += dx;
            y += dy;
            xx += dx * dx;
            xy += dx * dy;
            yy += dy * dy;
        }
        let variance = xx - x * x / n;
        self.slope = if variance > 0. { (xy - x * y / n) / variance } else { 0. };
        self.intercept = (y - self.slope * x) / n;
        self.jitter = ((yy - y * y / n - self.slope * (xy - x * y / n)) / n).max(0.).sqrt();
    }
    /// Oldest point in a train of consistent intervals that depart from a previous
    /// period. A delayed packet and the shorter interval that follows it do not qualify.
    pub fn confirmed_step_start(&self, previous: f64, noise_us: f64) -> Option<(i64, i64)> {
        self.confirmed_step(previous, noise_us).map(|(start, _)| start)
    }

    pub(crate) fn confirmed_step(&self, previous: f64, noise_us: f64) -> Option<((i64, i64), u8)> {
        // Two nearly identical intervals can distinguish a large jump from a
        // delayed packet followed by a short one. Keep the four-interval noise
        // test for ordinary changes and for devices with appreciable jitter.
        self.step_intervals(previous, 2, 0.30, noise_us * 8., 0.03)
            .map(|head| (head, 2))
            .or_else(|| self.step_intervals(previous, 4, 0.08, noise_us * 2., 0.4).map(|head| (head, 4)))
    }

    fn step_intervals(&self, previous: f64, count: usize, bpm_fraction: f64, noise_floor: f64, tolerance: f64) -> Option<(i64, i64)> {
        if self.len <= count {
            return None;
        }
        let first = (self.cursor + N - count - 1) % N;
        let start = self.points[first];
        let (index, end) = self.last?;
        let pulses = index.saturating_sub(start.0) as f64;
        let period = end.saturating_sub(start.1) as f64 / pulses;
        let change = period - previous;
        // BPM is reciprocal period. Allow for the microsecond rounding of the endpoints.
        if !(2500. ..=500_000.).contains(&period) || change.abs() + 1. / pulses < period * bpm_fraction || change.abs() < noise_floor {
            return None;
        }
        // Timestamp jitter moves neighbouring intervals in opposite directions. Its
        // observed amplitude can justify a wider agreement band, while every interval
        // must still depart from the old period in the direction of this change.
        let jitter_margin = if count == 2 { (0.40 * noise_floor).min(change.abs() * 0.25) } else { (1.7 * noise_floor).min(change.abs() * 0.95) };
        let band = (change.abs() * tolerance).max(jitter_margin);
        for i in 0..count {
            let (a, start) = self.points[(first + i) % N];
            let (b, end) = self.points[(first + i + 1) % N];
            let interval = end.saturating_sub(start) as f64 / b.saturating_sub(a) as f64;
            if (interval - period).abs() > band {
                return None;
            }
        }
        Some(start)
    }

    /// Prediction requires several independently observed intervals at the fitted rate.
    pub(crate) fn regular_intervals(&self, period: f64) -> bool {
        const COUNT: usize = 4;
        if self.len <= COUNT {
            return false;
        }
        let start = (self.cursor + N - COUNT - 1) % N;
        (0..COUNT).all(|i| {
            let elapsed = self.points[(start + i + 1) % N].1.saturating_sub(self.points[(start + i) % N].1);
            (elapsed as f64 - period).abs() <= (0.02 * period).max(2.)
        })
    }

    /// Detect sustained tempo motion without changing the stable linear period/phase estimates.
    /// With evenly spaced pulse indices, the centred quadratic is orthogonal to both a constant
    /// and a linear slope. A constant-speed clock therefore contributes no curvature.
    pub(crate) fn is_tempo_ramp(&self) -> bool {
        if self.len < 24 || self.slope <= 0. {
            return false;
        }
        let Some((last, stamp)) = self.last else { return false };
        let first = (self.cursor + N - self.len) % N;
        if last.saturating_sub(self.points[first].0) != self.len as i64 - 1 {
            return false;
        }
        let n = self.len as f64;
        let center = (n - 1.) / 2.;
        let variance = (n * n - 1.) / 12.;
        let norm = n * (n * n - 1.) * (n * n - 4.) / 180.;
        let projection = self.points[..self.len]
            .iter()
            .map(|&(i, t)| {
                let x = i.saturating_sub(last) as f64 + center;
                (x * x - variance) * t.saturating_sub(stamp) as f64
            })
            .sum::<f64>()
            .abs();
        // Reject stationary timestamp noise (three standard errors) and slow clock flutter.
        // Twice the quadratic coefficient is the change in pulse period per pulse.
        projection > 3. * self.jitter * norm.sqrt() && 2. * projection / norm > 0.00045 * self.slope * self.slope / 1_000_000.
    }

    pub fn period_us(&self) -> Option<f64> {
        (self.len >= 2 && self.slope > 0.).then_some(self.slope)
    }
    pub fn predict_us(&self, pulse: i64) -> Option<i64> {
        let (i, t) = self.last?;
        Some(t.saturating_add((self.intercept + self.period_us()? * (pulse.saturating_sub(i) as f64)).round() as i64))
    }
    pub fn jitter_us(&self) -> f64 {
        self.jitter
    }
}

#[derive(Debug, Copy, Clone, Eq, PartialEq, Default)]
pub enum State {
    #[default]
    Waiting,
    Locked,
    Coasting,
    Stopped,
}
#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum Action {
    Locate(i64),
    Play {
        pulse: i64,
        at: i64,
    },
    /// The input thread already submitted the prepared playback command.
    Started {
        pulse: i64,
        at: i64,
        render_from: i64,
    },
    Stop,
}
#[derive(Default, Clone, Copy, Debug)]
pub struct Snapshot {
    pub bpm: Option<f64>,
    /// The wire confirmed a tempo step during uninterrupted playback within the past beat.
    pub recovering_tempo_step: bool,
    /// The source has a sustained tempo trend above its measured timestamp noise.
    pub tempo_ramp: bool,
    /// Number of intervals used if the latest F8 confirmed a new tempo.
    pub step_intervals: u8,
    /// The input is delivering groups of F8s with shared timing.
    pub packed_delivery: bool,
    pub jitter_us: f64,
    pub phase_error_us: i64,
    pub state: State,
    pub dropouts: u64,
    /// Most recently played musical clock number, separate from the tempo estimator counter.
    pub pulse: i64,
    pub stamp_us: i64,
    pub now_us: i64,
}

struct PreparedResume;
pub(crate) struct Follower {
    pub(crate) cue: Option<PreparedResume>,
    pub(crate) source: Option<u8>,
    pub(crate) coast: bool,
    pub(crate) waiting_for_output: bool,
    state: State,
    awaiting_clock: Option<i64>,
    pub(crate) next_pulse: i64,
    fit_index: i64,
    // Three F8s within one millisecond cannot be individual beats in the
    // supported tempo range. Keep each pulse and fit completed groups by their final ordinal.
    packet_head: Option<(i64, i64)>,
    packed_delivery: bool,
    singleton_groups: u8,
    previous_batch_noise: [f64; 4],
    short: PulseFit<12>,
    steady: PulseFit<192>,
    changes: u8,
    step_pulses_left: u8,
    step_intervals: u8,
    latest: Option<i64>,
    coast_period_us: Option<f64>,
    played_stamp: i64,
    played_pulse: i64,
    phase_error_us: i64,
    dropouts: u64,
    events: [Option<Action>; 32],
    head: usize,
    queued_action: bool,
    count: usize,
    spp: Option<Option<u8>>,
}
impl Default for Follower {
    fn default() -> Self {
        Self {
            cue: None,
            source: None,
            coast: true,
            waiting_for_output: false,
            state: State::Waiting,
            awaiting_clock: None,
            next_pulse: 0,
            fit_index: 0,
            packet_head: None,
            packed_delivery: false,
            singleton_groups: 0,
            previous_batch_noise: [0.; 4],
            short: Default::default(),
            steady: Default::default(),
            changes: 0,
            step_pulses_left: 0,
            step_intervals: 0,
            latest: None,
            played_stamp: 0,
            played_pulse: 0,
            coast_period_us: None,
            phase_error_us: 0,
            dropouts: 0,
            events: [None; 32],
            head: 0,
            queued_action: false,
            count: 0,
            spp: None,
        }
    }
}
impl Follower {
    fn push(&mut self, action: Action) {
        if !matches!(action, Action::Play { .. }) {
            self.cue = None;
            self.step_pulses_left = 0;
        }
        self.queued_action = true;
        if self.count == self.events.len() {
            // A paused host cannot replay an arbitrarily long history safely.
            // Resynchronise on a fresh Start/Continue after delivering one Stop.
            self.events.fill(None);
            self.head = 0;
            self.count = 1;
            self.events[0] = Some(Action::Stop);
            self.state = State::Stopped;
            self.awaiting_clock = None;
            return;
        }
        self.events[(self.head + self.count) % self.events.len()] = Some(action);
        self.count += 1;
    }
    pub(crate) fn take(&mut self) -> Option<Action> {
        if self.count == 0 {
            return None;
        }
        let a = self.events[self.head].take();
        self.head = (self.head + 1) % self.events.len();
        self.count -= 1;
        a
    }
    pub(crate) fn start_pending(&self) -> bool {
        self.awaiting_clock.is_some() || self.events.iter().flatten().any(|action| matches!(action, Action::Play { .. } | Action::Started { .. }))
    }

    pub(crate) fn coalesced_render(&self) -> bool {
        self.state == State::Locked && self.packed_delivery
    }

    pub(crate) fn render_through_pulse(&self) -> Option<i64> {
        match self.state {
            // Inside a coalesced transfer the tiny inter-arrival time gives no
            // evidence for an undelivered pulse. Release events as their F8 arrives.
            State::Locked if self.packed_delivery => Some(self.played_pulse),
            State::Locked => Some(self.played_pulse.saturating_add(1)),
            State::Stopped => Some(self.played_pulse),
            State::Waiting | State::Coasting => None,
        }
    }

    pub(crate) fn render_prediction(&self) -> Option<(i64, f64)> {
        let period = self.steady.period_us()?;
        if self.state != State::Locked
            || self.step_pulses_left != 0
            || self.packed_delivery
            || !(2500. ..=500_000.).contains(&period)
            || !self.short.regular_intervals(period)
            || self.steady.is_tempo_ramp()
        {
            return None;
        }
        Some((self.latest?, period))
    }

    fn bpm(&self) -> Option<f64> {
        self.steady.period_us().or_else(|| self.short.period_us()).filter(|p| (2500. ..=500_000.).contains(p)).map(|p| 2_500_000. / p)
    }
    pub(crate) fn snapshot(&self, now_us: i64) -> Snapshot {
        Snapshot {
            // The gap before the first USB batch can look like a much slower clock.
            // Do not retime the session until three intervals can identify a batch.
            bpm: (self.fit_index >= 4).then(|| self.bpm()).flatten().or_else(|| self.coast_period_us.map(|p| 2_500_000. / p)),
            recovering_tempo_step: self.step_pulses_left > 0,
            tempo_ramp: self.state == State::Locked && !self.packed_delivery && self.step_pulses_left == 0 && self.steady.is_tempo_ramp(),
            step_intervals: self.step_intervals,
            packed_delivery: self.packed_delivery,
            jitter_us: self.steady.jitter_us(),
            phase_error_us: self.phase_error_us,
            state: self.state,
            dropouts: self.dropouts,
            pulse: self.played_pulse,
            stamp_us: self.played_stamp,
            now_us,
        }
    }
    pub(crate) fn expire(&mut self, now: i64) {
        let period = self.bpm().map_or(0., |bpm| 2_500_000. / bpm);
        let mut timeout = (3. * period).ceil().max(150_000.) as i64;
        if self.packed_delivery
            && let Some((head, _)) = self.packet_head
        {
            // Some of the upcoming silence was already delivered in this batch.
            timeout = timeout.saturating_add(((self.fit_index - head) as f64 * period).round().min(150_000.) as i64);
        }
        if self.packed_delivery { timeout = if period <= 0. {1_500_000} else { timeout.max((15. * period).ceil() as i64 + 1000) }; }
        if self.latest.is_some_and(|last| now.saturating_sub(last) > timeout) {
            // Idle pulses can predate a fresh transport request by an entire timeout.
            let request = self.awaiting_clock.filter(|at| now.saturating_sub(*at) <= timeout);
            let cue = self.cue.take();
            self.lost();
            if request.is_some() {
                self.awaiting_clock = request;
                self.cue = cue;
            }
        }
    }
    pub(crate) fn lost(&mut self) {
        self.cue = None;
        self.coast_period_us = self.steady.period_us().or(self.coast_period_us);
        self.short.clear();
        self.steady.clear();
        self.latest = None;
        self.packet_head = None;
        self.packed_delivery = false;
        self.singleton_groups = 0;
        self.previous_batch_noise = [0.; 4];
        self.step_intervals = 0;
        self.changes = 0;
        self.step_pulses_left = 0;
        if self.state == State::Locked {
            self.dropouts = self.dropouts.saturating_add(1);
            if self.coast {
                self.state = State::Coasting;
            } else {
                self.state = State::Stopped;
                self.push(Action::Stop);
            }
        }
        self.awaiting_clock = None;
    }
    fn clock(&mut self, at: i64) {
        let at = self.latest.map_or(at, |prev| prev.max(at));
        self.latest = Some(at);
        self.fit_index = self.fit_index.saturating_add(1);
        self.step_intervals = 0;
        self.step_pulses_left = self.step_pulses_left.saturating_sub(1);
        if self.packet_head.is_none_or(|(_, stamp)| at.saturating_sub(stamp) > 1000) {
            if self.packed_delivery
                && let Some((head, stamp)) = self.packet_head
            {
                // A group can only reach the driver once its last pulse exists.
                // The first arrival timestamp is therefore an observation of the
                // previous group's last ordinal once the next group starts.
                self.observe_period(self.fit_index - 1, stamp);
                let width = self.fit_index - head;
                self.singleton_groups = if width == 1 { self.singleton_groups.saturating_add(1) } else { 0 };
                if self.singleton_groups >= 4 {
                    self.packed_delivery = false;
                    self.previous_batch_noise = [0.; 4];
                }
            }
            self.packet_head = Some((self.fit_index, at));
        }
        let (head, _) = self.packet_head.unwrap_or((self.fit_index, at));
        if !self.packed_delivery && self.fit_index - head >= 2 {
            self.packed_delivery = true;
            self.singleton_groups = 0;
            self.short.clear();
            self.steady.clear();
            self.changes = 0;
        }
        if !self.packed_delivery {
            self.observe_period(self.fit_index, at);
        }
        let start_requested = self.awaiting_clock.take().is_some();
        if self.state == State::Coasting && (start_requested || self.bpm().is_some()) {
            // F8 has no absolute position. Match the returning train to the nearest
            // pulse on the coasting grid. A lone tick after a timeout has no fitted tempo.
            if let Some(period) = self.coast_period_us {
                let coasted = (at.saturating_sub(self.played_stamp).max(0) as f64 / period).round() as i64;
                self.next_pulse = self.next_pulse.max(self.played_pulse.saturating_add(coasted));
            }
            self.state = State::Locked;
        }
        if start_requested {
            self.state = State::Locked;
            self.push(Action::Play { pulse: self.next_pulse, at });
        }
        if self.state == State::Locked {
            self.played_stamp = self.steady.predict_us(self.fit_index).unwrap_or(at);
            self.played_pulse = self.next_pulse;
            self.next_pulse = self.next_pulse.saturating_add(1);
        }
    }
    fn observe_period(&mut self, ordinal: i64, at: i64) {
        self.short.push(ordinal, at);
        // Long regression suppresses USB quantisation and timestamp jitter.
        // A sustained slope change outside the short fit's noise band starts a fresh epoch.
        if let (Some(fast), Some(slow)) = (self.short.period_us(), self.steady.period_us()) {
            let threshold = (0.013 * slow).max(0.35 * self.short.jitter_us());
            if (fast - slow).abs() > threshold {
                self.changes = self.changes.saturating_add(1);
            } else {
                self.changes = 0;
            }
            // Four batch heads can span twenty pulses. Use the noise floor from
            // before that candidate, so the step itself cannot mask the change.
            let mut noise = self.steady.jitter_us();
            if self.packed_delivery {
                self.previous_batch_noise.rotate_left(1);
                std::mem::swap(&mut noise, &mut self.previous_batch_noise[3]);
            }
            if let Some(((index, stamp), intervals)) = self.short.confirmed_step(slow, noise) {
                self.steady.clear();
                self.steady.push(index, stamp);
                self.changes = 0;
                if self.state == State::Locked {
                    self.step_intervals = intervals;
                    self.step_pulses_left = 24;
                }
            } else if self.changes >= 6 {
                self.steady.clear();
                self.changes = 0;
            }
        }
        self.phase_error_us = self.steady.predict_us(ordinal).map_or(0, |pred| at.saturating_sub(pred));
        self.steady.push(ordinal, at);
    }
    /// System common bytes may be interrupted by real-time messages, even inside SysEx.
    /// Channel data and incomplete or malformed system messages never trigger a transport action.
    pub(crate) fn receive(&mut self, bytes: &[u8], at: i64) -> bool {
        self.queued_action = false;
        self.expire(at);
        for &byte in bytes {
            match byte {
                0xf8 => self.clock(at),
                0xfa => {
                    self.state = State::Waiting;
                    self.next_pulse = 0;
                    self.awaiting_clock = Some(at);
                    self.push(Action::Locate(0));
                }
                0xfb => {
                    if self.state != State::Locked {
                        self.awaiting_clock = Some(at);
                    }
                }
                0xfc => {
                    self.awaiting_clock = None;
                    self.state = State::Stopped;
                    self.push(Action::Stop);
                }
                0xf9..=0xff => {}
                0xf2 => self.spp = Some(None),
                0..=0x7f => match self.spp {
                    Some(None) => self.spp = Some(Some(byte)),
                    Some(Some(low)) => {
                        self.spp = None;
                        if self.waiting_for_output || (matches!(self.state, State::Waiting | State::Stopped) && self.awaiting_clock.is_none()) {
                            // The clock can be locked before a device has ever presented sound.
                            // A new stopped insertion replaces that unrendered Continue.
                            if self.waiting_for_output {
                                self.state = State::Stopped;
                                self.awaiting_clock = None;
                            }
                            self.next_pulse = (i64::from(low) | i64::from(byte) << 7) * 6;
                            self.push(Action::Locate(self.next_pulse));
                        }
                    }
                    _ => {}
                },
                _ => self.spp = None,
            }
        }
        self.queued_action
    }
}

use std::cell::{Cell, RefCell};
use soundcraft_time::{SampleRate,TempoMap,TICKS_PER_QUARTER};
const TICKS_PER_PULSE:i64=TICKS_PER_QUARTER / 24;
struct MidiInputs{feed:Feed}
struct Feed{time:Cell<i64>,f:RefCell<Follower>}
impl MidiInputs{
 fn with_port_names(_:Vec<String>,_:Vec<String>)->Self{Self{feed:Feed{time:Cell::new(0),f:RefCell::new(Follower::default())}}}
 fn feed(&self)->&Feed {&self.feed}
}
impl Feed{
 fn set_clock(&self,t:i64){self.time.set(t);}
 fn receive(&self,_:u8,b:&[u8]){self.f.borrow_mut().receive(b,self.time.get());}
 fn ports(&self)->&Self{self}
 fn assign(&self,_:&str)->u8{0}
 fn set_clock_follow(&self,_:Option<u8>,coast:bool,_:i64,_:bool){self.f.borrow_mut().coast=coast;}
 fn clock_follow_status(&self,act:&mut Vec<Action>)->Snapshot{let mut f=self.f.borrow_mut();f.expire(self.time.get());while let Some(a)=f.take(){act.push(a);}f.snapshot(self.time.get())}
 fn clock_delivery(&self)->soundcraft_mix::ClockDelivery{if self.f.borrow().coalesced_render() {soundcraft_mix::ClockDelivery::Coalesced} else {soundcraft_mix::ClockDelivery::Wire}}
 fn clock_render_tick(&self)->Option<i64>{self.f.borrow().render_through_pulse().map(|p|p*TICKS_PER_PULSE)}
}
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
    let edit = if render_until > 0 && s.packed_delivery && s.recovering_tempo_step {
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
                if p == 0 {
                    // A single F8 starts transport at the same sample on both clocks.
                    times.push(ideal[0].round() as i64);
                    continue;
                }
                // Every coalesced group reaches the driver after its last source pulse.
                let width = n.min(ideal.len() - p);
                let last = ideal[p + width - 1].round() as i64;
                for j in 0..width {
                    times.push(last + j as i64 * 200);
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
            mixer.render_clock_block(&song, pos, frames, &mut block, feed.clock_render_tick(), feed.clock_delivery());
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
    if std::env::var_os("DUMP_VOICES").is_some() { eprintln!("VOICES {:?},{}, {} -> {} {:?}",mode,transition, from, to, hits.iter().map(|(t, v)| (*t, v.len())).collect::<Vec<_>>()); }
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
        record(&format!("A4-{name}"), &r, 28_800); eprintln!("A4_ERR {name} {:?}",r.attacks.iter().zip(&r.wire).enumerate().filter_map(|(k,(v,w))| if v.len()!=1 || (v[0]-w).abs()>1 {Some((k,v,w))}else {None}).take(8).collect::<Vec<_>>());
        valid &= r.steps.is_empty()
            && r.dropouts == 0
            && r.malformed == 0
            && r.unmatched == 0
            && r.attacks.iter().zip(&r.wire).all(|(v, wire)| matches!(v.as_slice(), [x] if (x-wire).abs() <= 1));
    }
    assert!(valid);
}

}