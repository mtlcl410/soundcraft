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
    /// A confirmed tempo step or brake needs a fast grid correction during playback.
    pub recovering_tempo_step: bool,
    /// A fast brake has reached long pulse intervals. Follow the arriving pulses
    /// themselves while the new tempo and phase settle.
    pub braking: bool,
    /// Grid speed estimated for the next confirmed pulse during acceleration out of a brake.
    /// Status and loss detection continue to use the measured source tempo.
    pub brake_grid_bpm: Option<f64>,
    /// Short-term slope for upcoming score events while tracking a measured phase excursion.
    pub phase_grid_bpm: Option<f64>,
    /// The source has a sustained tempo trend above its measured timestamp noise.
    pub tempo_ramp: bool,
    /// Number of intervals used if the latest F8 confirmed a new tempo.
    pub step_intervals: u8,
    /// The input is delivering groups of F8s with shared timing.
    pub packed_delivery: bool,
    pub wire_phase_pending: bool,
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

mod wire_step {
type Proposal = Option<((i64, i64), u8)>;

#[derive(Clone, Copy, Default)]
struct Point {
    stamp: i64,
    prior_period: f64,
    prior_noise: f64,
}

/// Online least-squares fit with centered sums. One update per input pulse.
#[derive(Default)]
struct Slope {
    count: u32,
    mean_x: f64,
    mean_y: f64,
    xx: f64,
    xy: f64,
    yy: f64,
}

impl Slope {
    fn add(&mut self, x: f64, y: f64) {
        self.count = self.count.saturating_add(1);
        let (dx, dy) = (x - self.mean_x, y - self.mean_y);
        self.mean_x += dx / f64::from(self.count);
        self.mean_y += dy / f64::from(self.count);
        self.xx += dx * (x - self.mean_x);
        self.xy += dx * (y - self.mean_y);
        self.yy += dy * (y - self.mean_y);
    }

    fn period_noise(&self) -> Option<(f64, f64)> {
        let period = self.xy / self.xx;
        (2_500.0..=500_000.0).contains(&period).then(|| (period, ((self.yy - self.xy * period) / f64::from(self.count)).max(0.).sqrt()))
    }
}

struct Candidate {
    start: (i64, i64),
    prior: Point,
    fit: Slope,
}

/// A percent threshold is a comparison with the clock *before* the transition.
/// Near 8%, freeze the old fit while accumulating a new, independent slope.
#[derive(Default)]
pub(super) struct WireStep {
    recent: [Point; 32],
    seen: u8,
    next_check: i64,
    candidate: Option<Candidate>,
}

impl WireStep {
    pub(super) fn observe(&mut self, pulse: i64, stamp: i64, old: f64, noise: f64, proposed: Proposal) -> Proposal {
        let slot = |p: i64| p.rem_euclid(32) as usize;
        self.recent[slot(pulse)] = Point { stamp, prior_period: old, prior_noise: noise };
        self.seen = self.seen.saturating_add(1);
        if self.seen < 32 || pulse < self.next_check {
            return proposed;
        }
        // Take the old estimate before the four-interval candidate and before its onset
        // could have contaminated the long fit. Recent observations still drive phase.
        let prior = self.recent[slot(pulse.saturating_sub(12))];
        let recent = stamp.saturating_sub(self.recent[slot(pulse.saturating_sub(4))].stamp) as f64 / 4.;
        // A just-restarted long fit can have only two noisy points. Verify the
        // pre-transition plateau independently before treating it as a reference.
        let before = self.recent[slot(pulse.saturating_sub(8))].stamp.saturating_sub(self.recent[slot(pulse.saturating_sub(28))].stamp) as f64 / 20.;
        let reliable = (prior.prior_period / before - 1.).abs() < 0.025;
        let fraction = (before / recent - 1.).abs();
        // Near 8%, four intervals at this precision cannot resolve a tenth of a percent.
        // Keep the ordinary short path for clear jumps outside that uncertainty band.
        if let Some(((_, start), intervals)) = proposed {
            let period = stamp.saturating_sub(start) as f64 / f64::from(intervals);
            if (before / period - 1.).abs() > 0.14 {
                self.candidate = None;
                self.next_check = pulse.saturating_add(17);
                return proposed;
            }
        }
        if self.candidate.is_none() && reliable && (0.052..=0.14).contains(&fraction) {
            self.candidate = Some(Candidate { start: (pulse, stamp), prior, fit: Default::default() });
        }
        let c = self.candidate.as_mut()?;
        let n = pulse.saturating_sub(c.start.0);
        c.fit.add(n as f64, stamp.saturating_sub(c.start.1) as f64);
        let Some((new, noise_after)) = c.fit.period_noise() else {
            if n > 4 {
                self.candidate = None;
            }
            return None;
        };
        if n < 4 || (c.prior.prior_noise > 30. && n < 16) {
            return None;
        }
        let delta = (c.prior.prior_period / new - 1.).abs();
        let n_f = n as f64;
        // Standard error of an equally spaced least-squares slope, with independent
        // errors before and after the change. Endpoint rounding adds one microsecond.
        let error = (12.0_f64.sqrt() * 4. * (c.prior.prior_noise / (192. * 192_f64.sqrt()) + noise_after / (n_f * n_f.sqrt())) + 1. / n_f) / new;
        let resolved = if delta - error >= 0.08 {
            Some(true)
        } else if delta + error < 0.08 {
            Some(false)
        } else if error <= 0.00045 {
            // Within rounding/measurement resolution the 8% boundary is inclusive.
            Some(true)
        } else if n >= 159 {
            Some(delta >= 0.08)
        } else {
            None
        };
        if let Some(step) = resolved {
            let start = c.start;
            self.candidate = None;
            self.next_check = pulse.saturating_add(17);
            return step.then_some((start, n.min(159) as u8));
        }
        None
    }
}

}
pub(crate) struct Follower {
    edge: wire_step::WireStep,
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
    // Two beats and their shared endpoint. Let measured BPM settle after a temporary nudge.
    settling: PulseFit<49>,
    // Variance of wire jitter independent of the long fit's response to a tempo bend.
    wire_noise_variance: f64,
    readout_pulses_left: u8,
    phase_pulses_left: u8,
    short: PulseFit<12>,
    steady: PulseFit<192>,
    changes: u8,
    step_pulses_left: u8,
    step_intervals: u8,
    latest: Option<i64>,
    // Wire history survives Coast. A fresh pair in the new acquisition epoch
    // replaces the old period; the silence between epochs is never a beat.
    wire_stamps: [i64; 13],
    wire_points: usize,
    last_wire_interval: Option<i64>,
    previous_wire_interval: Option<i64>,
    brake_pulses_left: u8,
    last_sensing_byte: Option<i64>,
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
            edge: Default::default(),
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
            settling: Default::default(),
            wire_noise_variance: 0.,
            readout_pulses_left: 0,
            phase_pulses_left: 0,
            short: Default::default(),
            steady: Default::default(),
            changes: 0,
            step_pulses_left: 0,
            step_intervals: 0,
            latest: None,
            wire_stamps: [0; 13],
            wire_points: 0,
            last_wire_interval: None,
            previous_wire_interval: None,
            brake_pulses_left: 0,
            last_sensing_byte: None,
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
            self.phase_pulses_left = 0;
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
            // While braking or consuming one USB batch, the wire does not yet
            // establish the next pulse's time.
            State::Locked if self.brake_pulses_left > 0 || self.phase_tracking() || self.packed_delivery => Some(self.played_pulse),
            State::Locked => Some(self.played_pulse.saturating_add(1)),
            State::Stopped => Some(self.played_pulse),
            State::Waiting | State::Coasting => None,
        }
    }

    pub(crate) fn render_prediction(&self) -> Option<(i64, f64)> {
        let period = self.steady.period_us()?;
        if self.state != State::Locked
            || self.step_pulses_left != 0
            || self.brake_pulses_left != 0
            || self.phase_tracking()
            || self.packed_delivery
            || !(2500. ..=500_000.).contains(&period)
            || !self.short.regular_intervals(period)
            || self.steady.is_tempo_ramp()
        {
            return None;
        }
        Some((self.latest?, period))
    }

    /// At a steady or gently changing rate, independent timestamp noise is better
    /// rejected by the long fit. An abrupt or sustained rate excursion takes priority.
    fn prefer_steady_phase(&self) -> bool {
        self.wire_noise_variance > 850. * 850.
            && self.readout_pulses_left == 0
            && self.short.period_us().zip(self.steady.period_us()).is_some_and(|(short, long)| (short - long).abs() < 0.025 * long)
    }
    fn phase_tracking(&self) -> bool {
        self.state == State::Locked
            && self.phase_pulses_left > 0
            && !self.prefer_steady_phase()
            && self.step_pulses_left == 0
            && self.brake_pulses_left == 0
            && !self.packed_delivery
    }
    fn phase_period(&self) -> Option<f64> {
        let last = self.last_wire_interval?;
        let prior = self.previous_wire_interval?;
        if last.abs_diff(prior) <= 2 && last >= 2_500 {
            // An ideal source may round two successive intervals in opposite directions.
            return Some((last + prior) as f64 / 2.);
        }
        let recent = self.wire_stamps[12].saturating_sub(self.wire_stamps[8]) as f64 / 4.;
        if self.steady.period_us().is_some_and(|period| (recent - period).abs() > 0.05 * period) { Some(recent) } else { self.short.period_us() }
    }

    fn observe_phase_arrival(&mut self, at: i64) {
        self.phase_pulses_left = self.phase_pulses_left.saturating_sub(1);
        if self.packed_delivery || self.wire_points != self.wire_stamps.len() || self.step_pulses_left != 0 {
            return;
        }
        let (Some(last), Some(period)) = (self.latest, self.steady.period_us()) else { return };
        let noise = self.steady.jitter_us();
        let interval_error = (at.saturating_sub(last) as f64 - period).abs();
        let interval_changed = interval_error > (5. * noise).max(0.012 * period).max(30.);
        let phase_changed = noise < 1_000.
            && self.steady.predict_us(self.fit_index.saturating_add(1)).is_some_and(|expected| at.abs_diff(expected) as f64 > (3. * noise).max(350.));
        if interval_changed || phase_changed {
            // A deck can bend its speed below the eight-percent step threshold.
            // Stop committing ahead of the wire while the latest phase is moving.
            self.phase_pulses_left = 48;
        }
    }
    fn bpm(&self) -> Option<f64> {
        let fit = self.steady.period_us().or_else(|| self.short.period_us());
        let fit = if self.state == State::Locked && self.readout_pulses_left > 0 && self.settling.jitter_us() < 950. {
            self.settling.period_us().or(fit)
        } else {
            fit
        };
        let period = match self.brake_pulses_left {
            0 => fit,
            1..=36 => self.short.period_us().or(fit),
            _ => self.last_wire_interval.map(|p| p as f64).or(fit),
        }?;
        // At 5 BPM, two timestamps with ±1 ms jitter can enclose a 502 ms interval.
        (2_500. ..=502_000.).contains(&period).then(|| 2_500_000. / period.clamp(2_500., 500_000.))
    }
    fn brake_grid_bpm(&self) -> Option<f64> {
        if self.brake_pulses_left <= 36 || self.wire_points != self.wire_stamps.len() {
            return None;
        }
        let last = self.last_wire_interval? as f64;
        let w = &self.wire_stamps;
        let older = w[8].saturating_sub(w[4]) as f64 / 4.;
        let recent = w[12].saturating_sub(w[8]) as f64 / 4.;
        let shortening = (older - recent) / 4.;
        if recent <= 0. || shortening <= 0.012 * recent {
            return None;
        }
        // Match the advancing wire while the render cursor can already be several
        // pulses ahead. The confirmed-pulse horizon still gates every note.
        let period = (recent - 4. * shortening).clamp(last / 2., last);
        Some((2_500_000. / period).clamp(5., 1000.))
    }

    pub(crate) fn snapshot(&self, now_us: i64) -> Snapshot {
        Snapshot {
            // The gap before the first USB batch can resemble a much slower clock.
            // Three intervals allow the follower to distinguish that startup burst.
            bpm: (self.fit_index >= 4).then(|| self.bpm()).flatten().or_else(|| self.coast_period_us.map(|p| 2_500_000. / p)),
            recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0,
            braking: self.brake_pulses_left > 0,
            brake_grid_bpm: self.brake_grid_bpm(),
            phase_grid_bpm: self.phase_tracking().then(|| self.phase_period()).flatten().map(|p| 2_500_000. / p),
            tempo_ramp: self.state == State::Locked && !self.packed_delivery && self.step_pulses_left == 0 && self.steady.is_tempo_ramp(),
            step_intervals: self.step_intervals,
            packed_delivery: self.packed_delivery,
            wire_phase_pending: {
                let [a,b,c] = [self.wire_stamps[10], self.wire_stamps[11], self.wire_stamps[12]];
                let gap = c.saturating_sub(b);
                let last = b.saturating_sub(a);
                if self.packed_delivery {
                    self.steady.period_us().is_none()
                } else {
                    self.wire_points >= 3 && (gap <= 1000 || (last >= 2500 && gap > last + last / 2))
                }
            },
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
        let period = self.bpm().map(|bpm| 2_500_000. / bpm);
        // The first pulse of an acquisition has no interval yet. Give even a
        // 5 BPM source time to provide a second pulse, also when returning from Coast.
        let timeout = match (period, self.last_wire_interval) {
            (None, _) if self.short.period_us().is_none() && self.steady.period_us().is_none() => 1_500_000,
            (fitted, interval) => {
                let last = interval.unwrap_or(0);
                let growth = if self.brake_pulses_left > 0 { last.saturating_sub(self.previous_wire_interval.unwrap_or(last)).max(0) } else { 0 };
                let expected = fitted.unwrap_or(0.).max(last.saturating_add(growth) as f64);
                // Timestamped groups of up to five pulses can be followed by
                // a whole group's silence even when the preceding group was short.
                let group_gap = if self.packed_delivery { 3. * 5. * fitted.unwrap_or(0.) + 1_000. } else { 0. };
                (3. * expected).max(group_gap).ceil().clamp(150_000., 1_500_000.) as i64
            }
        };
        let cable_lost = self.last_sensing_byte.is_some_and(|last| now.saturating_sub(last) > 300_000);
        if cable_lost {
            self.last_sensing_byte = None;
        }
        if self.latest.is_some_and(|last| cable_lost || now.saturating_sub(last) > timeout) {
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
        self.coast_period_us = self.bpm().map(|bpm| 2_500_000. / bpm).or(self.coast_period_us);
        self.short.clear();
        self.steady.clear();
        self.settling.clear();
        self.readout_pulses_left = 0;
        self.wire_noise_variance = 0.;
        self.phase_pulses_left = 0;
        self.latest = None;
        self.edge = Default::default();
        self.wire_points = 0;
        self.packet_head = None;
        self.packed_delivery = false;
        self.singleton_groups = 0;
        self.previous_batch_noise = [0.; 4];
        self.step_intervals = 0;
        self.brake_pulses_left = 0;
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
    /// Three consecutive four-pulse spans isolate a sustained brake from a single
    /// tempo step. A smooth period increase produces a quadratic time curve; compare
    /// the growth with residual timing noise before leaving the long jitter filter.
    fn braking_trend(&self) -> bool {
        let w = &self.wire_stamps;
        if self.wire_points < w.len() {
            return false;
        }
        let first = w[4].saturating_sub(w[0]) as f64;
        let middle = w[8].saturating_sub(w[4]) as f64;
        let last = w[12].saturating_sub(w[8]) as f64;
        let growth = (middle - first).min(last - middle);
        if growth <= 2_000. || middle <= 1.05 * first || last <= 1.05 * middle {
            return false;
        }
        // A step in the middle of the window increases both four-interval spans,
        // but the last six intervals settle onto the new tempo. A continuing brake
        // must also grow between the two halves of that most recent span.
        if w[12].saturating_sub(w[9]) <= w[9].saturating_sub(w[6]) {
            return false;
        }
        // A single big interval change is a tempo step, even when a four-pulse
        // span straddles the transition. A brake widens over multiple intervals.
        let largest_jump = w.windows(3).map(|t| t[2].saturating_sub(t[1]) as f64 - t[1].saturating_sub(t[0]) as f64).fold(0., f64::max);
        // The outer spans each contain four intervals. A single jump accounting
        // for 80% of their mean-period difference signifies a step.
        if largest_jump >= 0.8 * ((last - first) / 4.) {
            return false;
        }
        let slope = w[12].saturating_sub(w[0]) as f64 / 12.;
        let curvature = (w[12].saturating_sub(w[6]) as f64 - w[6].saturating_sub(w[0]) as f64) / 72.;
        w.iter().enumerate().all(|(index, stamp)| {
            let x = index as f64 - 6.;
            let residual = stamp.saturating_sub(w[6]) as f64 - x * (slope + x * curvature);
            2. * residual.abs() < growth
        })
    }

    fn observe_wire_interval(&mut self, at: i64) {
        if self.brake_pulses_left == 1 && self.wire_points == self.wire_stamps.len() {
            // Seed the normal fit with the settled end of the ramp; its older
            // history describes a different speed and phase.
            self.steady.clear();
            for (index, stamp) in self.wire_stamps.iter().enumerate() {
                self.steady.push(self.fit_index - 12 + index as i64, *stamp);
            }
        }
        self.brake_pulses_left = self.brake_pulses_left.saturating_sub(1);
        self.wire_stamps.rotate_left(1);
        self.wire_stamps[12] = at;
        self.wire_points = (self.wire_points + 1).min(self.wire_stamps.len());
        let Some(previous) = self.latest else { return };
        let gap = at.saturating_sub(previous).min(1_500_000);
        if self.packed_delivery || gap <= 1_000 {
            self.brake_pulses_left = 0;
            return;
        }
        let changing = self.last_wire_interval.is_some_and(|last| gap.abs_diff(last) > (last / 16).max(4_000) as u64);
        if self.braking_trend() || (self.brake_pulses_left > 0 && changing) {
            // Hold the score at the last confirmed wire pulse through the brake
            // and the subsequent acceleration, then settle back over two beats.
            self.brake_pulses_left = 48;
        }
        if let Some(previous_gap) = self.last_wire_interval {
            // A second difference cancels constant period and phase. With independent
            // timestamp errors its variance is (1² + 2² + 1²) times their variance.
            // Bound isolated transport or driver discontinuities in the running estimate.
            let change = (gap - previous_gap).clamp(-7_000, 7_000) as f64;
            self.wire_noise_variance += 0.025 * (change * change / 6. - self.wire_noise_variance);
        }
        self.previous_wire_interval = self.last_wire_interval;
        self.last_wire_interval = Some(gap);
    }

    fn clock(&mut self, at: i64) {
        let at = self.latest.map_or(at, |prev| prev.max(at));
        self.observe_phase_arrival(at);
        self.observe_wire_interval(at);
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
            self.settling.clear();
            self.readout_pulses_left = 0;
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
            self.played_stamp = match self.brake_pulses_left {
                0 if self.phase_tracking() => at,
                0 => self.steady.predict_us(self.fit_index).unwrap_or(at),
                1..=36 => self.short.predict_us(self.fit_index).unwrap_or(at),
                _ => at,
            };
            self.played_pulse = self.next_pulse;
            self.next_pulse = self.next_pulse.saturating_add(1);
        }
    }
    fn observe_period(&mut self, ordinal: i64, at: i64) {
        self.readout_pulses_left = self.readout_pulses_left.saturating_sub(1);
        if let Some((recent, long)) = self.settling.period_us().zip(self.steady.period_us())
            && (recent - long).abs() > 0.007 * long
        {
            // A meaningful rate change can settle in two beats. Give the long fit
            // its full window to forget the old rate before switching the display back.
            self.readout_pulses_left = 192;
        }
        self.settling.push(ordinal, at);
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
            let proposed = self.short.confirmed_step(slow, noise);
            let step = if self.packed_delivery { proposed } else { self.edge.observe(ordinal, at, slow, noise, proposed) };
            if !self.packed_delivery
                && self.step_pulses_left == 0
                && let (Some(short_phase), Some(steady_phase)) = (self.short.predict_us(ordinal), self.steady.predict_us(ordinal))
                && (short_phase.abs_diff(steady_phase) as f64 > (3. * self.short.jitter_us()).max(950.)
                    || self.short.jitter_us() < 5. && (fast - slow).abs() > 0.01 * slow)
            {
                self.phase_pulses_left = 48;
            }
            if let Some(((index, stamp), intervals)) = step {
                self.steady.clear();
                self.steady.push(index, stamp);
                self.changes = 0;
                if self.state == State::Locked {
                    self.step_intervals = intervals;
                    self.phase_pulses_left = 0;
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
        if !bytes.is_empty() && (self.last_sensing_byte.is_some() || bytes.contains(&0xfe)) {
            self.last_sensing_byte = Some(self.last_sensing_byte.map_or(at, |last| last.max(at)));
        }
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
 fn receive(&self,p:u8,b:&[u8]){if p==0 {self.f.borrow_mut().receive(b,self.time.get());}}
 fn ports(&self)->&Self{self}
 fn assign(&self,n:&str)->u8{u8::from(n=="other")}
 fn set_clock_follow(&self,_:Option<u8>,coast:bool,_:i64,_:bool){self.f.borrow_mut().coast=coast;}
 fn clock_follow_status(&self,act:&mut Vec<Action>)->Snapshot{let mut f=self.f.borrow_mut();f.expire(self.time.get());while let Some(a)=f.take(){act.push(a);}f.snapshot(self.time.get())}
 fn clock_delivery(&self)->soundcraft_mix::ClockDelivery { if self.f.borrow().coalesced_render() {soundcraft_mix::ClockDelivery::Coalesced} else {soundcraft_mix::ClockDelivery::Wire} }
 fn clock_render_tick(&self)->Option<i64>{self.f.borrow().render_through_pulse().map(|p|p*TICKS_PER_PULSE)}
}
fn update_grid(grid: &mut TempoMap, anchor: Option<(i64, i64)>, waiting_tick: i64, s: Snapshot, sr: SampleRate, render_until: i64) -> bool {
    if s.wire_phase_pending { return false; }
    let Some(bpm) = s.brake_grid_bpm.or(s.phase_grid_bpm).or(s.bpm) else { return false };
    let Some((origin, stamp)) = anchor else {
        if s.state == State::Waiting && (grid.tempo_at_tick(waiting_tick) - bpm).abs() >= 0.05 {
            let _ = grid.set_tempo(waiting_tick, bpm);
            return true;
        }
        return false;
    };
    let tick = s.pulse.saturating_mul(TICKS_PER_PULSE);
    let writable = grid.samples_to_ticks(render_until, sr).saturating_add(1);
    let start = grid.tick_to_samples(origin.saturating_mul(TICKS_PER_PULSE), sr);
    let elapsed = sr.samples(s.stamp_us.saturating_sub(stamp) as f64 / 1e6);
    let phase = sr.seconds(start.saturating_add(elapsed).saturating_sub(grid.tick_to_samples(tick, sr)));
    if s.state != State::Locked || s.pulse <= origin {
        return false;
    }
    // With a clean source, reach the next pulse when measured grid phase drifts out
    // of tolerance. Retain the wider jitter deadband for noisy and batched delivery.
    let tracking = s.phase_grid_bpm.is_some();
    // A smoothly drifting, low-noise clock needs fewer published tempo events.
    let phase_deadband = if tracking || s.jitter_us >= 1. { 0.0012 } else { 0.0026 };
    let precise = !s.recovering_tempo_step && !s.packed_delivery && !s.braking && s.jitter_us < 1_400. && phase.abs() > phase_deadband;
    let correcting = s.recovering_tempo_step || tracking || precise;
    let edit = if render_until > 0 && (precise || tracking || (s.packed_delivery || s.braking) && s.recovering_tempo_step) {
        writable.max(origin.saturating_mul(TICKS_PER_PULSE))
    } else {
        tick.max(writable)
    };
    let check_tick = if correcting { edit } else { tick };
    if !tracking && !precise && grid.tempos().last().is_some_and(|event| event.tick > check_tick) {
        return false;
    }
    let before = grid.tempos().partition_point(|event| event.tick <= check_tick);
    let last_edit_tick = grid.tempos()[..before].last().map_or(0, |event| event.tick);
    let since_edit = check_tick.saturating_sub(last_edit_tick);
    let slope = grid.tempo_at_tick(check_tick);
    // A confirmed tempo step should reach the next unrendered beat even when a minor
    // correction was just published. Small jitter corrections retain the usual spacing.
    let tempo_step = (slope - bpm).abs() >= slope * 0.08;
    let spacing = if precise || tracking {
        0
    } else if s.recovering_tempo_step || s.tempo_ramp {
        2
    } else {
        6
    };
    if !tempo_step && since_edit < spacing * TICKS_PER_PULSE {
        return false;
    }
    let (bpm_deadband, phase_deadband) = if correcting && s.jitter_us > 50. {
        (0.03, 0.001)
    } else if s.tempo_ramp {
        (0.035, 0.0005)
    } else {
        (0.15, 0.003)
    };
    if (slope - bpm).abs() < bpm_deadband && phase.abs() < phase_deadband && !precise {
        return false;
    }
    if correcting {
        // Join the new wire grid at a future pulse. Only the interval after
        // the committed audio changes; then restore the source's exact tempo.
        let edit_sample = grid.tick_to_samples(edit, sr);
        let elapsed_at_edit = sr.seconds(edit_sample.saturating_sub(start).saturating_sub(elapsed));
        let wire_at_edit = tick as f64 + elapsed_at_edit * bpm * TICKS_PER_QUARTER as f64 / 60.;
        let ahead = (edit as f64).max(wire_at_edit);
        // On a low-noise nudge, retain at least 30% of an interval for the bridge.
        // A larger correction has a full pulse of headroom.
        let headroom = if tracking { 0.30 } else { 1. };
        let join = ((ahead / TICKS_PER_PULSE as f64 + headroom).ceil() as i64).saturating_mul(TICKS_PER_PULSE);
        if join <= edit {
            return false;
        }
        let seconds = (join as f64 - wire_at_edit) * 60. / (bpm * TICKS_PER_QUARTER as f64);
        let bridge = (join - edit) as f64 * 60. / (seconds * TICKS_PER_QUARTER as f64);
        if tracking || precise {
            // A replacement bridge starts after committed audio. Only its old future
            // join can overlap the revised slope.
            while let Some(tick) = grid.tempos().last().map(|event| event.tick).filter(|t| *t > edit) {
                grid.remove_tempo(tick);
            }
        }
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


mod history {
//! Bound the transient follow grid while retaining the timing of live takes and current playback.
use soundcraft_time::{Range, SampleRate, TempoEvent, TempoMap};

const HISTORY_CAP: usize = 512;

#[derive(Default)]
pub(super) struct History {
    pub(super) next_check: usize,
    /// The old and compacted time maps resume the same slope and sample at this tick.
    pub(super) last_join: Option<i64>,
}

impl History {
    pub(super) fn has_take_credit(&self) -> bool {
        self.next_check > HISTORY_CAP
    }

    pub(super) fn should_compact(&self, grid: &TempoMap) -> bool {
        grid.tempos().len() > self.next_check.max(HISTORY_CAP)
    }

    pub(super) fn compact(&mut self, grid: &mut TempoMap, sr: SampleRate, origin: i64, take_ranges: Vec<Range>) {
        // Include the interval at each take edge: a sample can fall between two integer ticks.
        let mut protected: Vec<_> = take_ranges
            .into_iter()
            .map(|r| {
                let start = grid.samples_to_ticks(r.start, sr).saturating_sub(1);
                let end = grid.samples_to_ticks(r.end, sr).saturating_add(1);
                (start, end)
            })
            .collect();
        // Only the interval containing Start/Continue must keep its slope. Exact
        // bridges reproduce its starting sample even when the SPP is hours into the score.
        protected.push((origin, origin));
        protected.sort_unstable();
        // Only compact old *complete* intervals. Keep half the cap as a recent window.
        let old_len = grid.tempos().len().saturating_sub(HISTORY_CAP / 2);
        let mut ranges = protected.as_slice();
        // Use exactly the cumulative ticks/BPM addition order of TempoMap. Independent
        // sums per run would round differently after the joins, especially on half-samples.
        let mut elapsed = 0.;
        let mut previous: Option<TempoEvent> = None;
        let segments: Vec<_> = grid
            .tempos()
            .iter()
            .take(old_len.saturating_add(1))
            .map(|&event| {
                if let Some(prev) = previous {
                    elapsed += event.tick.saturating_sub(prev.tick) as f64 / prev.bpm;
                }
                previous = Some(event);
                (event, elapsed)
            })
            .collect();
        let mut run_start = 0;
        let mut changed = false;
        for (index, pair) in segments.windows(2).enumerate() {
            let [(a, _), (b, _)] = pair else { continue };
            if references(&mut ranges, a.tick, b.tick) {
                if let Some(run) = segments.get(run_start..=index) {
                    changed |= compress_run(grid, run);
                }
                run_start = index + 1;
            }
        }
        if let Some(run) = segments.get(run_start..) {
            changed |= compress_run(grid, run);
        }
        if changed {
            self.last_join = segments.last().map(|(event, _)| event.tick);
        }
        let events = grid.tempos();
        let mut ranges = protected.as_slice();
        let ends = events.iter().skip(1).map(|next| next.tick).chain(std::iter::once(i64::MAX));
        let needed = events.iter().zip(ends).filter(|(e, end)| references(&mut ranges, e.tick, *end)).count();
        // Credit only retained take events. One position anchor is already included
        // in the 512-event allowance. An old, completed take cannot inflate the budget
        // as unrelated revisions arrive, and an open take can keep its required history.
        self.next_check = HISTORY_CAP.saturating_add(needed.saturating_sub(1));
    }
}

fn references(ranges: &mut &[(i64, i64)], start: i64, end: i64) -> bool {
    while let Some((range, rest)) = ranges.split_first() {
        if range.1 >= start {
            return range.0 < end;
        }
        *ranges = rest;
    }
    false
}

/// A bridge replaces the interior changes. Its weighted harmonic mean preserves elapsed
/// time at the far edge; rounding to samples here would accumulate error across passes.
fn compress_run(grid: &mut TempoMap, events: &[(TempoEvent, f64)]) -> bool {
    let [(first, start), middle @ .., (last, end)] = events else { return false };
    if middle.is_empty() {
        return false;
    }
    let ticks = last.tick.saturating_sub(first.tick) as f64;
    let bpm = ticks / (end - start);
    // Division is rounded too. Only drop the intervening knots if this bridge reconstructs
    // the *exact* accumulated endpoint. A different rounding pair can need two bridges.
    if let Some(exact) =
        [bpm, bpm.next_down(), bpm.next_up()].into_iter().find(|&candidate| (5.0..=1000.).contains(&candidate) && start + ticks / candidate == *end)
    {
        if grid.set_tempo(first.tick, exact).is_err() {
            return false;
        }
        for (event, _) in middle.iter().rev() {
            grid.remove_tempo(event.tick);
        }
        return true;
    }
    let mid = events.len() / 2;
    let (Some(left), Some(right)) = (events.get(..=mid), events.get(mid..)) else { return false };
    let first_changed = compress_run(grid, left);
    compress_run(grid, right) || first_changed
}

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

fn score_window(song: &mut Session, first: usize, total: usize) -> Result<(), &'static str> {
    for (track_index, stride) in [1, 2].into_iter().enumerate() {
        let clip = &mut song.tracks[track_index].playlist_mut().unwrap().clips[0];
        let ClipContent::Midi { sequence } = &mut clip.content else { return Err("the DJ score must contain MIDI clips") };
        // first moves forward only. The window starts full and only shrinks for the final section.
        sequence.notes.truncate(total.saturating_sub(first).div_ceil(stride));
        for (i, note) in sequence.notes.iter_mut().enumerate() {
            let eighth = first + i * stride;
            note.start = eighth as i64 * 480;
            note.velocity = 32 + (eighth % TAGS) as u8 * 6;
        }
    }
    Ok(())
}

/// Each tag has a distinct velocity and an independently rendered native-pitch waveform.
/// Comparing the entire voice checks its release as well as its attack.
fn templates() -> &'static [Vec<f32>] {
    static REFERENCE: OnceLock<Vec<Vec<f32>>> = OnceLock::new();
    REFERENCE.get_or_init(|| {
        let mut song = band_song(120., TAGS, 192_000);
        score_window(&mut song, 0, TAGS).unwrap();
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
    let mut history = history::History::default();
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
                score_window(&mut song, (p / 12).saturating_sub(16), expected.len()).unwrap();
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
            if update_grid(&mut song.tempo, Some((0, ORIGIN + arrivals_us[0])), 0, snap, sr, pos + 1440) && history.should_compact(&song.tempo) {
                history.compact(&mut song.tempo, sr, 0, Vec::new());
            }
            result.tempo_events = result.tempo_events.max(song.tempo.tempos().len());
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
                mix.render_clock_block(&song, pos, count, &mut output, feed.clock_render_tick(), feed.clock_delivery());
            }
            for (i, &rendered) in output[0][..count].iter().enumerate() {
                let value = if running { rendered } else { 0. };
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
    result
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
impl Delivery {
    fn cycle(self) -> usize {
        match self {
            Self::Burst(n) => n,
            Self::VariableBurst => 3 + 4 + 5,
            Self::Jitter(_) => 1,
        }
    }
}

fn delivery_times(ideal: &[f64], mode: Delivery, first_group: usize, jitter: i64) -> Vec<i64> {
    let mut seed = 42u64;
    let mut times: Vec<i64> = ideal
        .iter()
        .enumerate()
        .map(|(pulse, stamp)| {
            let amplitude = if let Delivery::Jitter(v) = mode { v } else { jitter };
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            let delta = ((seed >> 32) % (2 * amplitude + 1) as u64) as i64 - amplitude;
            stamp.round() as i64 + if pulse == 0 { 0 } else { delta }
        })
        .collect();
    if matches!(mode, Delivery::Jitter(_)) {
        return times;
    }
    let mut start = first_group;
    let mut group = 0;
    while start < times.len() {
        let width = if let Delivery::Burst(n) = mode { n } else { 3 + group % 3 };
        let end = (start + width).min(times.len());
        // Driver delivery starts only after the group's last pulse exists.
        let last = times[end - 1];
        for (j, stamp) in times[start..end].iter_mut().enumerate() {
            *stamp = last + j as i64 * 200;
        }
        start = end;
        group += 1;
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
    render_delivery(from, to, transition, n, mode, 1, 0)
}
fn render_delivery(from: f64, to: f64, transition: usize, n: usize, mode: Delivery, first_group: usize, jitter: i64) -> Observation {
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
    let times = delivery_times(&ideal, mode, first_group, jitter);
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
                for phase in 0..mode.cycle() {
                    let r = render_delivery(from, to, change, change + 193, mode, 1 + phase, 0);
                    let label = format!("{from}-{to}-{change}-{mode:?}-phase{phase}");
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
    }
    assert!(valid, "a packed slowdown lost or damaged a voice, or exceeded the attack or wire-relative tolerance");
}

#[test]
fn first_usb_batches_mid_song_render_at_their_wire_time() {
    let verbose = std::env::var_os("SOUNDCRAFT_PACKET_TRACE").is_some();
    let mut valid = true;
    for bpm in [120., 148.] {
        for mode in [Delivery::Burst(3), Delivery::Burst(4), Delivery::Burst(5), Delivery::VariableBurst] {
            for phase in 0..mode.cycle() {
                let start = 384 + phase;
                for jitter in [0, 1000] {
                    let r = render_delivery(bpm, bpm, start, start + 193, mode, start, jitter);
                    let label = format!("{bpm}-{mode:?}-phase{phase}-jitter{jitter}");
                    valid &= r.unmatched == 0 && r.malformed == 0 && r.dropouts == 0 && r.attacks.iter().all(|v| v.len() == 1);
                    let first = start.div_ceil(12);
                    let mut late = 0;
                    let mut early = 0;
                    for k in first..r.attacks.len() {
                        let [error] = r.attacks[k].as_slice() else { continue };
                        let wire = r.wire[k];
                        let residual = error - wire;
                        late = late.max(residual);
                        early = early.min(*error);
                        valid &= *error >= -48 && residual <= if k == first { 480 } else { 288 };
                        if verbose {
                            eprintln!("ONSET_NOTE {label} eighth={k} wire_samples={wire} measured_samples={error} residual_samples={residual}");
                        }
                    }
                    eprintln!(
                        "ONSET {label} worst_late_samples={late} earliest_samples={early} missing={} extra={} damaged={} dropouts={}",
                        r.attacks.iter().filter(|v| v.is_empty()).count(),
                        r.unmatched + r.attacks.iter().map(|v| v.len().saturating_sub(1)).sum::<usize>(),
                        r.malformed,
                        r.dropouts
                    );
                }
            }
        }
    }
    assert!(valid, "switching from individual Clock to a USB batch exceeded the wire-relative lateness or grid earliness limit");
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
    let missing = r.attacks.iter().filter(|slot| slot.is_empty()).count();
    let repeated: usize = r.attacks.iter().map(|slot| slot.len().saturating_sub(1)).sum();
    eprintln!(
        "{name}: {} scored eighths, {missing} missing, {repeated} repeated, {} unmatched, {} changed waveforms, open tail {}",
        r.attacks.len(),
        r.extra,
        r.damaged,
        r.tail_open
    );
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
                eprintln!("{name}: readout after two beats {settle:.4} BPM");
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
                assert!(r.snapshots.iter().all(|s| !s.braking), "{name}: an abrupt tempo ratio triggered the continuous brake response");
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
    // Arrival batching is a declared delivery transition. Keep its wire-relative
    // errors and the inclusive percentile visible beside the steady-state result.
    let mut all_stable = Vec::new();
    let mut individual = Vec::new();
    let mut batched = 0;
    let mut max_late = 0;
    let mut earliest = 0;
    let mut within_wire = true;
    for (i, (&error, &transition)) in signed.iter().zip(&exclude).enumerate() {
        if transition {
            continue;
        }
        all_stable.push(error.abs());
        let pulse = i * 12;
        if burst.contains(&pulse) {
            let wire = ((arrived[pulse] - ideal[pulse]).max(0) as f64 * 0.048).round() as i64;
            let residual = error - wire;
            max_late = max_late.max(residual);
            earliest = earliest.min(error);
            within_wire &= error >= -48 && residual <= if batched == 0 { 480 } else { 288 };
            eprintln!("DJ8_NOTE eighth={i} wire_samples={wire} measured_samples={error} residual_samples={residual}");
            batched += 1;
        } else {
            individual.push(error.abs());
        }
    }
    let percentile = |a: &mut Vec<i64>| {
        a.sort_unstable();
        a[(a.len() * 999).div_ceil(1000) - 1]
    };
    let p999 = percentile(&mut individual);
    eprintln!(
        "20 tracks, {} eighths, {} outside transitions, p99.9 {p999} samples; including burst {} samples; {batched} batched eighths, max signed late beyond wire {max_late} samples, earliest vs grid {earliest} samples; max {} grid events",
        signed.len(),
        individual.len(),
        percentile(&mut all_stable),
        r.tempo_events
    );
    assert!(within_wire, "the transition to grouped F8 crossed the wire-relative lateness or grid earliness limit");
    assert!(p999 <= 192);
    assert!(r.tempo_events <= 512, "unreferenced grid events during a live mix");
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

mod ramp_response {
use super::sampler_song::sampler_song;
use super::*;

#[test]
fn continuous_pitch_fader_round_trip_keeps_eighths_in_phase() {
    let sr = SampleRate::HZ_48000;
    let mut ok = true;
    for (bars, delta) in [(16, 0.3), (32, 124. * 0.08), (32, -124. * 0.08)] {
        let n = bars * 96;
        for jitter in [0_i64, 1000, 2000] {
            let inputs = MidiInputs::with_port_names(vec![], vec!["deck".into()]);
            let feed = inputs.feed();
            let port = feed.ports().assign("deck");
            feed.set_clock_follow(Some(port), true, 0, false);
            feed.set_clock(20_000);
            feed.receive(port, &[0xfa]);
            let count = n * 2 / 12 + 1;
            let mut song = sampler_song(TempoMap::new(124., 4, 4).unwrap(), sr, count, 48000 * 180);
            let mut mix = soundcraft_mix::MixEngine::new(48000., 128);
            let mut block = vec![vec![0.; 128]; 2];
            let mut pcm = Vec::<f32>::new();
            let mut render_to = |end: i64, song: &soundcraft_model::Session| {
                while (pcm.len() as i64) < end {
                    let start = pcm.len() as i64;
                    let frames = (end - start).min(128) as usize;
                    mix.render_with_clock_limit(song, start, frames, &mut block, feed.clock_render_tick());
                    pcm.extend_from_slice(&block[0][..frames]);
                }
            };
            let mut seed = 42_u64;
            let mut us = 0.0_f64;
            let mut actions = Vec::new();
            let mut expected = Vec::new();
            let mut steps = 0;
            let mut recovering = false;
            let mut last = None;
            let mut jump = 0.0_f64;
            let mut rate_lag = 0.0_f64;
            let mut fit_bias = 0.0_f64;
            let mut signed = Vec::new();
            let mut ramp_pulses = 0;
            for i in 0..=2 * n {
                seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                let noise = if i == 0 { 0 } else { ((seed >> 32) % (2 * jitter + 1) as u64) as i64 - jitter };
                let at = us.round() as i64 + noise;
                // Render up to the next arrival with only the previous packet available.
                render_to(sr.samples(at as f64 / 1e6), &song);
                feed.set_clock(at + 20_000);
                feed.receive(port, &[0xf8]);
                let snap = feed.clock_follow_status(&mut actions);
                ramp_pulses += usize::from(snap.tempo_ramp);
                if i % 12 == 0 {
                    expected.push(sr.samples(us / 1e6));
                }
                let bpm = 124. + delta * (1. - (i as f64 / n as f64 - 1.).abs());
                if let Some(b) = snap.bpm {
                    // The tempo estimator acquires within one beat. Ignore the initial estimate.
                    if i >= 24 && snap.state == State::Locked {
                        if let Some(prev) = last {
                            jump = jump.max(f64::abs(b - prev));
                        }
                        rate_lag = rate_lag.max((b - bpm).abs());
                        fit_bias = fit_bias.max((snap.stamp_us as f64 - 20000. - us).abs() / 1000.);
                    }
                    last = Some(b);
                }
                steps += usize::from(snap.recovering_tempo_step && !recovering);
                recovering = snap.recovering_tempo_step;
                update_grid(&mut song.tempo, Some((0, 20000)), 0, snap, sr, sr.samples(at as f64 / 1e6 + 0.030));
                us += 2_500_000. / bpm;
            }
            let end = expected.last().unwrap() + 48000;
            render_to(end, &song);
            let mut edges = Vec::new();
            let mut active = None;
            for (i, &v) in pcm.iter().enumerate() {
                if v.abs() > 0.001 {
                    active.get_or_insert(i);
                } else if let Some(begin) = active.take() {
                    edges.push((begin, i));
                }
            }
            assert_eq!(edges.len(), expected.len());
            let reference = &pcm[edges[0].0..edges[0].1];
            assert_eq!(reference.len(), 96);
            for (&(on, off), &master) in edges.iter().zip(&expected) {
                assert_eq!(&pcm[on..off], reference);
                signed.push(on as i64 - master);
            }
            assert!(pcm[edges.last().unwrap().1..].iter().all(|x| *x == 0.));
            let peak = signed.iter().map(|v| v.abs()).max().unwrap() as f64 / 48.;
            eprintln!(
                "RAMP d={delta:.2} jitter={jitter} peak={peak:.4} last={} hits={count} false_steps={steps} adaptive={ramp_pulses} locked_jump={jump:.5} estimator_bpm_error={rate_lag:.5} fitted_stamp_error_ms={fit_bias:.5} samples={signed:?}",
                signed.last().unwrap()
            );
            ok &= peak <= 4. && steps == 0 && jump <= 0.1 && (delta.abs() > 1. || ramp_pulses == 0);
        }
    }
    assert!(ok);
}

}

mod large_steps {
use super::sampler_song::sampler_song;
use super::*;

fn edges(pcm: &[f32]) -> Vec<(i64, i64)> {
    let mut attack = 0;
    let mut previous = false;
    let mut hits = Vec::new();
    for (i, &v) in pcm.iter().enumerate() {
        let sounding = v.abs() > 0.001;
        if sounding && !previous {
            attack = i as i64;
        } else if !sounding && previous {
            hits.push((attack, i as i64));
        }
        previous = sounding;
    }
    hits
}

#[test]
fn tempo_steps_keep_every_rendered_eighth_and_its_waveform() {
    let sr = SampleRate::HZ_48000;
    let mut passed = true;
    for (before, after) in [(130., 80.), (120., 100.), (180., 60.), (100., 120.), (80., 130.), (60., 180.)] {
        for transition in [384_usize, 396] {
            let inputs = MidiInputs::with_port_names(vec![], vec!["drums".into()]);
            let feed = inputs.feed();
            let device = feed.ports().assign("drums");
            feed.set_clock_follow(Some(device), true, 0, false);
            feed.set_clock(0);
            feed.receive(device, &[0xfa]);
            let count = (transition + 192) / 12 + 1;
            let mut song = sampler_song(TempoMap::new(before, 4, 4).unwrap(), sr, count, 48_000 * 60);
            let mut mixer = soundcraft_mix::MixEngine::new(48_000., 128);
            let mut block = vec![vec![0.; 128]; 2];
            let mut pcm = Vec::new();
            let mut events = Vec::new();
            let mut expected = Vec::new();
            let mut us = 0.0_f64;
            // Feed only the current F8. Render to the next arrival before publishing its grid.
            // The 30 ms guard represents audio that a grid edit can no longer rewrite.
            for pulse in 0..=transition + 192 {
                let stamp = us.round() as i64;
                feed.set_clock(stamp);
                feed.receive(device, &[0xf8]);
                let snap = feed.clock_follow_status(&mut events);
                update_grid(&mut song.tempo, Some((0, 0)), 0, snap, sr, sr.samples(us / 1e6 + 0.030));
                if pulse % 12 == 0 {
                    expected.push(sr.samples(us / 1e6));
                }
                us += 2_500_000. / if pulse < transition { before } else { after };
                let end = if pulse == transition + 192 { expected.last().unwrap() + 48_000 } else { sr.samples(us / 1e6) };
                while (pcm.len() as i64) < end {
                    let pos = pcm.len() as i64;
                    let frames = (end - pos).min(128) as usize;
                    mixer.render_with_clock_limit(&song, pos, frames, &mut block, feed.clock_render_tick());
                    pcm.extend_from_slice(&block[0][..frames]);
                }
            }
            let hits = edges(&pcm);
            assert_eq!(hits.len(), expected.len(), "onset count {before}->{after} at {transition}");
            assert_eq!(hits[transition / 12].0, expected[transition / 12], "the boundary already played at the old tempo");
            let reference = &pcm[hits[0].0 as usize..hits[0].1 as usize];
            assert_eq!(reference.len(), 96);
            for &(on, off) in &hits {
                assert_eq!(&pcm[on as usize..off as usize], reference);
            }
            assert!(pcm[hits.last().unwrap().1 as usize..].iter().all(|x| x.abs() < 0.001));
            let signed: Vec<_> = hits.iter().zip(&expected).skip(transition / 12).map(|(hit, at)| (hit.0 - at) as f64 / 48.).collect();
            eprintln!("STEP {before}->{after} pulse={transition} hits={} ms={signed:.3?}", hits.len());
            passed &= signed[0].abs() <= 4. && signed[1].abs() <= 10. && signed[2..].iter().all(|e| e.abs() <= 4.);
        }
    }
    assert!(passed, "rendered eighth-note phase after a tempo step");
}

#[test]
fn early_device_render_waits_for_the_wire_and_keeps_the_located_attack() {
    let inputs = MidiInputs::with_port_names(vec![], vec!["drums".into()]);
    let feed = inputs.feed();
    let port = feed.ports().assign("drums");
    feed.set_clock_follow(Some(port), true, 0, false);
    feed.set_clock(0);
    feed.receive(port, &[0xfa]);
    feed.receive(port, &[0xf8]);
    let song = sampler_song(TempoMap::new(120., 4, 4).unwrap(), SampleRate::HZ_48000, 2, 48000);
    let mut mix = soundcraft_mix::MixEngine::new(48000., 128);
    let mut pcm = Vec::new();
    let mut block = vec![vec![0.; 128]; 2];
    // Start rendering 30 ms ahead, with only the first wire pulse in hand.
    let mut pos = 1440;
    mix.start_midi_at(0);
    let mut render = |end: i64, pcm: &mut Vec<f32>| {
        while pos < end {
            let n = (end - pos).min(128) as usize;
            mix.render_with_clock_limit(&song, pos, n, &mut block, feed.clock_render_tick());
            pcm.extend_from_slice(&block[0][..n]);
            pos += n as i64;
        }
    };
    for pulse in 1..=10 {
        render(1440 + pulse * 1000, &mut pcm);
        feed.set_clock(pulse * 1_000_000 / 48);
        feed.receive(port, &[0xf8]);
    }
    render(14000, &mut pcm);
    assert_eq!(edges(&pcm), vec![(0, 96)], "the second hat must wait for pulse 11");
    feed.set_clock(280_000);
    feed.receive(port, &[0xf8]);
    render(14400, &mut pcm);
    let hits = edges(&pcm);
    assert_eq!(hits.len(), 2);
    assert!(hits[1].0 >= 14000 - 1440);
    assert_eq!(hits[1].1 - hits[1].0, 96);
    assert_eq!(&pcm[..96], &pcm[hits[1].0 as usize..hits[1].1 as usize]);
}

}
