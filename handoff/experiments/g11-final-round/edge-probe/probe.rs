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
mod wire_step {type Proposal = Option<((i64, i64), u8)>;

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
pub(super) struct WireStep {
    recent: [Point; 32],
    seen: u8,
    next_check: i64,
    candidate: Option<Candidate>,
}

impl Default for WireStep {
    fn default() -> Self {
        Self { recent: [Point::default(); 32], seen: 0, next_check: 0, candidate: None }
    }
}

impl WireStep {
    pub(super) fn observe(&mut self, pulse: i64, stamp: i64, old: f64, noise: f64, proposed: Proposal) -> Proposal {
        let slot = |p: i64| p.rem_euclid(32) as usize;
        self.recent[slot(pulse)] = Point { stamp, prior_period: old, prior_noise: noise };
        self.seen = self.seen.saturating_add(1);
        if self.seen < 32 || pulse < self.next_check {
            if std::env::var_os("EDGE_DEBUG").is_some() && proposed.is_some(){eprintln!("PASS {pulse} old{old} prop{proposed:?}");} return proposed;
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
                if std::env::var_os("EDGE_DEBUG").is_some() && proposed.is_some(){eprintln!("PASS {pulse} old{old} prop{proposed:?}");} return proposed;
            }
        }
        if self.candidate.is_none() && reliable && (0.052..=0.14).contains(&fraction) {
            if std::env::var_os("EDGE_DEBUG").is_some() {eprintln!("CAND {pulse} old {} recent {recent} fraction{fraction}",prior.prior_period);} self.candidate = Some(Candidate { start: (pulse, stamp), prior, fit: Default::default() });
        }
        let Some(c) = self.candidate.as_mut() else { return None };
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
            if std::env::var_os("EDGE_DEBUG").is_some() {eprintln!("DONE {pulse} from {} delta{delta} n{n} old{} new{new} error{error} step{step}",c.start.0,c.prior.prior_period);} let start = c.start;
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
            State::Locked if self.brake_pulses_left > 0 || self.packed_delivery => Some(self.played_pulse),
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
        let fit = self.steady.period_us().or_else(|| self.short.period_us());
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
        self.previous_wire_interval = self.last_wire_interval;
        self.last_wire_interval = Some(gap);
    }

    fn clock(&mut self, at: i64) {
        let at = self.latest.map_or(at, |prev| prev.max(at));
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
                0 => self.steady.predict_us(self.fit_index).unwrap_or(at),
                1..=36 => self.short.predict_us(self.fit_index).unwrap_or(at),
                _ => at,
            };
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
            let proposed = self.short.confirmed_step(slow, noise);
            let step = if self.packed_delivery { proposed } else { self.edge.observe(ordinal, at, slow, noise, proposed) };
            if let Some(((index, stamp), intervals)) = step {
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

#[test]
fn classify() {
    let mut wrong=0;
    for amplitude in [0,1000] {for pct in [-8.1_f64,-8.,-7.9,7.9,8.,8.1] {
        let mut trials=Vec::new();
        for trial in 0..10 {
            if std::env::var_os("EDGE_DEBUG").is_some() && (amplitude!=0 || pct!=8. || trial>0) {continue;}
            let cut=384+trial; let mut t=0.0_f64; let mut seed=42+trial as u64;
            let mut f=Follower::default(); f.coast=true; f.receive(&[0xfa],0);
            let mut events=Vec::new();
            for p in 0..=cut+192 {
                seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                let at=t.round() as i64 + if p==0 {0}else{((seed>>32)%((amplitude*2+1) as u64)) as i64-amplitude};
                f.receive(&[0xf8],at); if f.step_intervals>0 {events.push(p as i64-cut as i64);}
                t+=2_500_000. / if p<cut {128.}else{128.*(1.+pct/100.)};
            }
            if (pct.abs()<8. && !events.is_empty()) || (pct.abs()>=8. && (events.len()!=1 || events[0]<1)) {wrong+=1;}
            trials.push(events);
        }
        eprintln!("CLASS {pct} jitter{amplitude}: {trials:?}");
    }}
    assert_eq!(wrong,0);
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



#[test]
fn nudge_and_staircase_classification() {
 for jitter in [0,1000] {
  for (pct,duration) in [-5.,-3.5,-2.,2.,3.5,5.].into_iter().flat_map(|pct|[500_000.,1_000_000.,2_000_000.].into_iter().map(move |duration| (pct,duration))).chain([(0.,0.)]) {
   let mut levels=vec![120.0_f64]; while *levels.last().unwrap()<132. {levels.push((*levels.last().unwrap()*1.01).min(132.));} while *levels.last().unwrap()>120. {levels.push((*levels.last().unwrap()*0.99).max(120.));}
   let mut f=Follower::default(); f.coast=true;f.receive(&[0xfa],0);
   let mut t=0.0_f64;let mut rng=42u64;let mut ev=vec![];
   for p in 0..=1032 {
    rng=rng.wrapping_mul(6364136223846793005).wrapping_add(1);let delta=if p==0{0}else{((rng>>32)%((2*jitter+1) as u64)) as i64-jitter};
    let at=t.round() as i64+delta;f.receive(&[0xf8],at);if f.step_intervals>0 {ev.push((p,f.step_intervals));}
    let end=384.*2_500_000./128.+duration;
    t+=if pct==0. {2_500_000./levels[if p<384{0}else{((p-384)/24+1).min(levels.len()-1)}]}else if p<384||t>=end{2_500_000./128.}else{let period=2_500_000./(128.*(1.+pct/100.));let left=end-t;if left>=period {period}else{left+(2_500_000./128.)*(1.-left/period)}};
   }
   eprintln!("OTHER {pct} {duration} {jitter}: {ev:?}");assert!(ev.is_empty());
  }
 }
}
