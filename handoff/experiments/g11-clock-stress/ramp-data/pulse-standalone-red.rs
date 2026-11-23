#![allow(dead_code)]
mod sync_input{//! MIDI driver timestamps have a per-connection epoch. Map them onto the
//! feed's monotonic (audio host) clock before comparing different callbacks.
#[cfg(any(test, target_os = "windows", target_os = "macos", target_os = "linux"))]
#[derive(Default)]
pub(crate) struct DriverTime {
    last: Option<(u64, i64)>,
    bucket: i64,
    minimum: i64,
    previous_min: Option<i64>,
}

#[cfg(any(test, target_os = "windows", target_os = "macos", target_os = "linux"))]
impl DriverTime {
    pub(crate) fn map(&mut self, stamp: u64, arrival: i64) -> i64 {
        let t = i64::try_from(stamp).unwrap_or(i64::MAX);
        let offset = arrival.saturating_sub(t);
        // The lower envelope rejects late deliveries, but cannot retain an epoch
        // forever: the driver's oscillator may run slower than the host's.
        let bucket = arrival.div_euclid(2_000_000);
        if self.last.is_none_or(|(last, _)| stamp < last) || bucket != self.bucket {
            self.previous_min = self.last.filter(|(last, _)| *last <= stamp).map(|(last, _)| {
                if bucket == self.bucket + 1 {
                    return self.minimum;
                }
                // Project only previously observed upward drift across a gap, capped at 200 ppm.
                // With a stable epoch the first delayed batch retains its learned mapping.
                let drift = self.previous_min.map_or(0, |previous| self.minimum.saturating_sub(previous).clamp(0, 400));
                let gap = stamp.saturating_sub(last);
                self.minimum.saturating_add((u128::from(gap) * drift as u128 / 2_000_000).min(i64::MAX as u128) as i64)
            });
            self.bucket = bucket;
            self.minimum = offset;
        } else {
            self.minimum = self.minimum.min(offset);
        }
        let estimate = self.previous_min.map_or(self.minimum, |last| last.min(self.minimum));
        let when = t.saturating_add(estimate).clamp(self.last.map_or(0, |(_, t)| t).min(arrival), arrival);
        self.last = Some((stamp, when));
        when
    }
}

/// Least-squares fit of host time in microseconds against an increasing MIDI pulse index.
/// Fixed capacity; restarting a transport or jumping backwards starts a new fit.
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
        // Two nearly identical intervals can distinguish a large jump from a
        // delayed packet followed by a short one. Keep the four-interval noise
        // test for ordinary changes and for devices with appreciable jitter.
        self.step_intervals(previous, 2, 0.30, noise_us * 8., 0.03).or_else(|| self.step_intervals(previous, 4, 0.08, noise_us * 2., 0.4))
    }

    fn step_intervals(&self, previous: f64, count: usize, bpm_fraction: f64, noise_floor: f64, tolerance: f64) -> Option<(i64, i64)> {
        if self.len <= count {
            return None;
        }
        let first = (self.cursor + N - count - 1) % N;
        let start = self.points[first];
        let (_, end) = self.last?;
        let period = end.saturating_sub(start.1) as f64 / count as f64;
        let change = period - previous;
        // BPM is reciprocal period. Allow for the microsecond rounding of the endpoints.
        if period <= 0. || change.abs() + 1. / (count as f64) < period * bpm_fraction || change.abs() < noise_floor {
            return None;
        }
        for i in 0..count {
            let interval = self.points[(first + i + 1) % N].1.saturating_sub(self.points[(first + i) % N].1) as f64;
            if (interval - period).abs() > change.abs() * tolerance {
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

}
mod clock_follow{//! Incoming MIDI Beat Clock. The input thread timestamps and interprets the wire;
//! the host drains only transport transitions. Ordinary clock ticks take no queue space.
use crate::sync_input::PulseFit;

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
    pub jitter_us: f64,
    pub phase_error_us: i64,
    pub state: State,
    pub dropouts: u64,
    /// Most recently played musical clock number, separate from the tempo estimator counter.
    pub pulse: i64,
    pub stamp_us: i64,
    pub now_us: i64,
}

pub(crate) struct PreparedResume{pulse:i64}
impl PreparedResume{fn dispatch(&self,_:impl FnOnce()->i64)->Option<i64>{None}}
pub(crate) struct Follower {
    pub(crate) cue: Option<PreparedResume>,
    pub(crate) source: Option<u8>,
    pub(crate) coast: bool,
    pub(crate) waiting_for_output: bool,
    state: State,
    awaiting_clock: Option<i64>,
    pub(crate) next_pulse: i64,
    fit_index: i64,
    short: PulseFit<12>,
    steady: PulseFit<192>,
    changes: u8,
    step_pulses_left: u8,
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
            short: Default::default(),
            steady: Default::default(),
            changes: 0,
            step_pulses_left: 0,
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
    pub(crate) fn arm(&mut self, port: u8, cue: PreparedResume) -> bool {
        if self.source == Some(port) && self.count == 0 && self.next_pulse == cue.pulse && matches!(self.state, State::Waiting | State::Stopped) {
            self.cue = Some(cue);
            return true;
        }
        false
    }

    pub(crate) fn dispatch_prepared(&mut self, now: impl FnOnce() -> i64) {
        if self.count == 1
            && let Some(Action::Play { pulse, at }) = self.events[self.head]
            && let Some(cue) = self.cue.take()
            && cue.pulse == pulse
            && let Some(render_from) = cue.dispatch(|| now().saturating_sub(at))
        {
            self.waiting_for_output = false;
            self.events[self.head] = Some(Action::Started { pulse, at, render_from });
        }
    }

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

    pub(crate) fn render_through_pulse(&self) -> Option<i64> {
        match self.state {
            State::Locked => Some(self.played_pulse.saturating_add(1)),
            State::Stopped => Some(self.played_pulse),
            State::Waiting | State::Coasting => None,
        }
    }

    pub(crate) fn render_prediction(&self) -> Option<(i64, f64)> {
        let period = self.steady.period_us()?;
        if self.state != State::Locked
            || self.step_pulses_left != 0
            || !(2500. ..=500_000.).contains(&period)
            || !self.short.regular_intervals(period)

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
            bpm: self.bpm().or_else(|| self.coast_period_us.map(|p| 2_500_000. / p)),
            recovering_tempo_step: self.step_pulses_left > 0,
            tempo_ramp: self.state == State::Locked && self.step_pulses_left == 0 && self.steady.is_tempo_ramp(),
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
        let timeout = self.bpm().map_or(150_000, |bpm| (7_500_000. / bpm).ceil() as i64).max(150_000);
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
        self.step_pulses_left = self.step_pulses_left.saturating_sub(1);
        self.short.push(self.fit_index, at);
        // Long regression suppresses USB quantisation and timestamp jitter.
        // A sustained slope change outside the short fit's noise band starts a fresh epoch.
        if let (Some(fast), Some(slow)) = (self.short.period_us(), self.steady.period_us()) {
            let threshold = (0.013 * slow).max(0.35 * self.short.jitter_us());
            if (fast - slow).abs() > threshold {
                self.changes = self.changes.saturating_add(1);
            } else {
                self.changes = 0;
            }
            if let Some((index, stamp)) = self.short.confirmed_step_start(slow, self.steady.jitter_us()) {
                self.steady.clear();
                self.steady.push(index, stamp);
                self.changes = 0;
                if self.state == State::Locked {
                    self.step_pulses_left = 24;
                }
            } else if self.changes >= 6 {
                self.steady.clear();
                self.changes = 0;
            }
        }
        self.phase_error_us = self.steady.predict_us(self.fit_index).map_or(0, |pred| at.saturating_sub(pred));
        self.steady.push(self.fit_index, at);
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

fn feed(r:&mut Follower,b:u8,at:i64){r.receive(&[b],at);}
#[test]
fn stable_device_prediction_waits_for_a_continuous_tempo_ramp_to_end() {
    let mut reader = Follower::default();
    let mut stamp = 0;
    feed(&mut reader, 0xfa, stamp);
    for _ in 0..192 {
        stamp += 20_000;
        feed(&mut reader, 0xf8, stamp);
    }
    assert!(reader.render_prediction().is_some());
    // Two microseconds per pulse is well inside short-term regularity tolerance,
    // yet the sustained slowdown is measurable across the long fit.
    for i in 1..=192 {
        stamp += 20_000 + 2 * i;
        feed(&mut reader, 0xf8, stamp);
    }
    let snapshot = reader.snapshot(stamp);
    assert!(snapshot.tempo_ramp && !snapshot.recovering_tempo_step);
    assert!(reader.short.regular_intervals(reader.steady.period_us().unwrap()));
    assert!(reader.render_prediction().is_none());
    for _ in 0..192 {
        stamp += 20_384;
        feed(&mut reader, 0xf8, stamp);
    }
    assert!(reader.render_prediction().is_some());
}
}
