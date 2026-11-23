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
    // supported tempo range. Keep every pulse, but fit only batch heads.
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
            bpm: self.bpm().or_else(|| self.coast_period_us.map(|p| 2_500_000. / p)),
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
                && let Some((head, _)) = self.packet_head
            {
                let width = self.fit_index - head;
                self.singleton_groups = if width == 1 { self.singleton_groups.saturating_add(1) } else { 0 };
                if self.singleton_groups >= 4 {
                    self.packed_delivery = false;
                    self.previous_batch_noise = [0.; 4];
                }
            }
            self.packet_head = Some((self.fit_index, at));
        }
        let (head, stamp) = self.packet_head.unwrap_or((self.fit_index, at));
        if !self.packed_delivery && self.fit_index - head >= 2 {
            self.packed_delivery = true;
            self.singleton_groups = 0;
            self.short.clear();
            self.steady.clear();
            self.short.push(head, stamp);
            self.steady.push(head, stamp);
            self.changes = 0;
        }
        if !self.packed_delivery || self.fit_index == head {
            self.observe_period(at);
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
    fn observe_period(&mut self, at: i64) {
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
        self.phase_error_us = self.steady.predict_us(self.fit_index).map_or(0, |pred| at.saturating_sub(pred));
        self.steady.push(self.fit_index, at);
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
fn gaussian(seed: &mut u64) -> f64 {
    let mut unit = || {
        *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        ((*seed >> 11) as f64 + 1.) / ((1u64 << 53) as f64 + 1.)
    };
    (-2. * unit().ln()).sqrt() * (std::f64::consts::TAU * unit()).cos()
}

#[test]
fn locks_and_predicts_pulses_across_tempos_jitter_and_usb_quantization() {
    for bpm in [90., 120., 174.] {
        for jitter in [500., 2000., 4000.] {
            let mut r = Follower::default();
            let mut seed = 100;
            let mut errors = Vec::new();
            let mut phase_errors = Vec::new();
            let interval = 60_000_000. / (24. * bpm);
            for pulse in 0..700 {
                let ideal = 100_000. + pulse as f64 * interval;
                let us = ((ideal + gaussian(&mut seed) * jitter) / 1000.).round() as i64 * 1000;
                r.receive(&[0xf8], us);
                if pulse == 23 {
                    assert!((r.bpm().unwrap() - bpm).abs() < 2., "failed to acquire within a beat");
                }
                if pulse >= 24 {
                    assert!(!r.steady.is_tempo_ramp(), "false ramp at {bpm} BPM/{jitter} us, pulse {pulse}");
                }
                if pulse >= 240 {
                    errors.push((r.bpm().unwrap() - bpm).abs());
                    phase_errors.push((r.phase_error_us as f64).abs());
                }
            }
            errors.sort_by(f64::total_cmp);
            phase_errors.sort_by(f64::total_cmp);
            let p95 = errors[errors.len() * 95 / 100];
            eprintln!("steady {bpm} {jitter} BPMp95={p95:.8} phasep95_us={:.4}", phase_errors[phase_errors.len() * 95 / 100]);
            if bpm == 120. && jitter == 2000. {
                assert!(errors.iter().all(|err| *err < 0.05), "steady-state BPM crossed the display tolerance");
            }
            assert!(p95 < if bpm == 120. && jitter <= 2000. { 0.05 } else { 0.25 }, "{bpm} BPM/{jitter} us: {p95}");
            assert!(phase_errors[phase_errors.len() * 95 / 100] <= jitter * 3.5 + 1000.);
        }
    }
}

