use super::{SampleRate, Snapshot};
use std::time::Instant;

/// Compare the physical playback clock with monotonic time over one continuous pass.
/// The MIDI reader's tempo and the recorded audio samples remain in their original domains.
#[derive(Default)]
pub(super) struct DeviceTime {
    first: Option<(u64, Instant, f64)>,
    next_us: Option<i64>,
    ratio: Option<f64>,
    /// The roll these measurements belong to.
    anchor: Option<(i64, i64)>,
    /// Correction (µs) at `pivot` µs after the origin, where the current ratio takes over.
    /// A replaced ratio applies from the start of its own window, so the projection of a
    /// wire time stays continuous instead of moving by the ratio change times the whole roll.
    pivot: i64,
    base: f64,
}

impl DeviceTime {
    fn correction(&self, delta: i64) -> f64 {
        self.base + self.ratio.map_or(0., |ratio| delta.saturating_sub(self.pivot) as f64 * (ratio - 1.))
    }

    pub(super) fn project(
        &mut self,
        mut wire: Snapshot,
        anchor: Option<(i64, i64)>,
        sr: SampleRate,
        observation: impl FnOnce() -> Option<(u64, Instant, f64)>,
    ) -> Snapshot {
        let Some((_, origin_us)) = anchor else {
            *self = Self::default();
            return wire;
        };
        // A Stop or locate and the next Play can be drained in one host call: a new roll
        // never inherits the previous roll's ratio.
        if self.anchor != anchor {
            *self = Self { anchor, ..Self::default() };
        }
        let delta = wire.stamp_us.saturating_sub(origin_us);
        if self.next_us.is_none_or(|at| wire.now_us >= at) {
            self.next_us = Some(wire.now_us.saturating_add(1_000_000));
            if let Some((pass, time, sample)) = observation() {
                if let Some((first_pass, start, base)) = self.first
                    && pass == first_pass
                    && time >= start
                {
                    let elapsed = time.duration_since(start).as_secs_f64();
                    if elapsed >= 20. {
                        let ratio = (sample - base) / (elapsed * sr.as_f64());
                        if (ratio - 1.).abs() <= 0.001 {
                            self.ratio = Some(ratio);
                        } else {
                            // An unusable stamp cannot undo the accumulated correction
                            // in the same roll. Start a fresh observation window, which
                            // continues the correction from here.
                            self.base = self.correction(delta);
                            self.pivot = delta;
                            self.first = Some((pass, time, sample));
                        }
                    }
                } else {
                    *self = Self { anchor, next_us: self.next_us, first: Some((pass, time, sample)), ..Self::default() };
                }
            }
        }
        let Some(ratio) = self.ratio else { return wire };
        wire.stamp_us = wire.stamp_us.saturating_add(self.correction(delta).round() as i64);
        wire.bpm = wire.bpm.map(|v| v / ratio);
        wire.phase_grid_bpm = wire.phase_grid_bpm.map(|v| v / ratio);
        wire.brake_grid_bpm = wire.brake_grid_bpm.map(|v| v / ratio);
        wire
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app::clock_follow::{State, TICKS_PER_PULSE, TempoMap, update_grid};
    use std::time::Duration;

    #[test]
    fn missing_observations_do_not_reset_the_grid_midpass_or_leak_into_a_new_start() {
        let mut device = DeviceTime::default();
        let start = Instant::now();
        let rate = SampleRate::HZ_48000;
        let wire = |s: i64| Snapshot { bpm: Some(120.), stamp_us: s * 1_000_000, now_us: s * 1_000_000, ..Snapshot::default() };
        let cue = Some((0, 0));
        device.project(wire(0), cue, rate, || Some((1, start, 0.)));
        let projected = device.project(wire(30), cue, rate, || Some((1, start + Duration::from_secs(30), 1_440_144.)));
        assert_eq!(projected.stamp_us, 30_003_000);
        let missing = device.project(wire(40), cue, rate, || None);
        assert_eq!(missing.stamp_us, 40_004_000);
        let stopped = device.project(wire(41), None, rate, || panic!("stopped transport cannot supply an observation"));
        assert_eq!(stopped.stamp_us, 41_000_000);
        let next = device.project(wire(42), Some((0, 42_000_000)), rate, || Some((2, start + Duration::from_secs(42), 0.)));
        assert_eq!(next.bpm, Some(120.));
    }

    #[test]
    fn a_new_roll_drained_in_the_same_call_as_its_stop_starts_without_the_old_ratio() {
        let mut device = DeviceTime::default();
        let start = Instant::now();
        let rate = SampleRate::HZ_48000;
        let wire = |us: i64| Snapshot { bpm: Some(120.), stamp_us: us, now_us: us, ..Snapshot::default() };
        device.project(wire(0), Some((0, 0)), rate, || Some((1, start, 0.)));
        let first = device.project(wire(30_000_000), Some((0, 0)), rate, || Some((1, start + Duration::from_secs(30), 1_440_144.)));
        assert_eq!(first.stamp_us, 30_003_000);
        // Stop and the next Play arrive together: the host never passes `None`, and the
        // previous roll's observation deadline has not passed yet.
        let next = device.project(wire(30_500_000), Some((0, 30_400_000)), rate, || Some((2, start + Duration::from_millis(30_500), 0.)));
        assert_eq!((next.stamp_us, next.bpm), (30_500_000, Some(120.)));
    }

    #[test]
    fn a_replaced_ratio_does_not_move_the_projected_stamp_at_two_hours() {
        let rate = SampleRate::HZ_48000;
        let mut device = DeviceTime::default();
        let start = Instant::now();
        // The device runs 40 ppm fast for two hours, then 120 ppm fast.
        let sample = |s: f64| if s <= 7200. { 48_000. * 1.000_04 * s } else { 48_000. * (1.000_04 * 7200. + 1.000_12 * (s - 7200.)) };
        let mut previous: Option<i64> = None;
        for seconds in 0..=7240_i64 {
            let us = seconds * 1_000_000;
            let wire = Snapshot { state: State::Locked, now_us: us, stamp_us: us, bpm: Some(120.), ..Snapshot::default() };
            // One unusable stamp rejects the window at 7180 s.
            let observed = sample(seconds as f64) + if seconds == 7180 { 48_000. * 0.002 * 7180. } else { 0. };
            let projected =
                device.project(wire, Some((0, 0)), rate, || Some((1, start + Duration::from_secs(seconds as u64), observed.round()))).stamp_us;
            let correction = projected - us;
            if let Some(previous) = previous {
                assert!((correction - previous).abs() < 4_000, "at {seconds} s the projection moved {} us", correction - previous);
            }
            previous = Some(correction);
        }
    }

    #[test]
    fn next_external_downbeat_uses_physical_samples_over_a_two_hour_pass() {
        let rate = SampleRate::HZ_48000;
        for ppm in [39., -40., 0.] {
            let mut device = DeviceTime::default();
            let mut grid = TempoMap::new(120., 4, 4).unwrap();
            let start = Instant::now();
            let actual_rate = 48_000. * (1. + ppm / 1e6);
            let mut max_ms = 0_f64;
            for seconds in 0..=7200_i64 {
                let pulse = seconds * 48;
                let stamp = seconds * 1_000_000;
                let wire = Snapshot { state: State::Locked, pulse, now_us: stamp, stamp_us: stamp, bpm: Some(120.), ..Snapshot::default() };
                let actual_sample = actual_rate * seconds as f64;
                let measured =
                    device.project(wire, Some((0, 0)), rate, || Some((1, start + Duration::from_secs(seconds as u64), actual_sample.round())));
                update_grid(&mut grid, Some((0, 0)), 0, measured, rate, actual_sample as i64 + 1440);
                let scheduled = grid.tick_to_samples((pulse + 24) * TICKS_PER_PULSE, rate);
                let error = (scheduled as f64 / actual_rate - seconds as f64 - 0.5) * 1000.;
                max_ms = max_ms.max(error.abs());
            }
            eprintln!("physical oscillator {ppm:+} ppm; maximum musical grid error {max_ms:.3} ms");
            assert!(max_ms < 4., "{ppm} ppm, {max_ms:.3} ms");
        }
    }
}
