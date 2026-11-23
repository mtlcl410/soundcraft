from pathlib import Path
src=Path('follow/crates/playback/src/clock_follow.rs'); dest=Path('dj-candidate')/src.relative_to('follow'); s=src.read_text()
s=s.replace('    short: PulseFit<12>,','''    // Period and phase before the newest four candidate intervals.
    previous_periods: [Option<f64>; 4],
    tracking_pulses: u8,
    short: PulseFit<12>,''').replace('            short: Default::default(),','            previous_periods: [None; 4],\n            tracking_pulses: 0,\n            short: Default::default(),')
s=s.replace('        self.short.clear();\n        self.steady.clear();','        self.short.clear();\n        self.previous_periods = [None; 4];\n        self.tracking_pulses = 0;\n        self.steady.clear();',1)
s=s.replace('        let fit = self.steady.period_us().or_else(|| self.short.period_us());','        let fit = if self.tracking_pulses > 0 { self.short.period_us() } else { self.steady.period_us() }.or_else(|| self.short.period_us());')
s=s.replace('0 => self.steady.predict_us(self.fit_index).unwrap_or(at),','0 if self.tracking_pulses > 0 => self.short.predict_us(self.fit_index).unwrap_or(at),\n                0 => self.steady.predict_us(self.fit_index).unwrap_or(at),')
s=s.replace('            recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0,','            recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0 || self.tracking_pulses > 0,')
s=s.replace('        self.short.push(self.fit_index, at);','''        let prior = if self.steady.is_tempo_ramp() { self.short.period_us() } else { self.steady.period_us() };
        let before_candidate = self.previous_periods[0];
        self.previous_periods.rotate_left(1);
        self.previous_periods[3] = prior;
        self.tracking_pulses = self.tracking_pulses.saturating_sub(1);
        self.short.push(self.fit_index, at);''')
s=s.replace('            if let Some(((index, stamp), intervals)) = self.short.confirmed_step(slow, noise) {','''            if !self.packed_delivery && self.step_pulses_left == 0
                && let (Some(short_phase), Some(long_phase)) = (self.short.predict_us(self.fit_index), self.steady.predict_us(self.fit_index))
                && short_phase.abs_diff(long_phase) as f64 > (4. * self.short.jitter_us()).max(1_250.)
            {
                self.tracking_pulses = 24;
            }
            let baseline = if self.packed_delivery { slow } else { before_candidate.unwrap_or(slow) };
            if (self.packed_delivery || self.step_pulses_left == 0) && let Some(((index, stamp), intervals)) = self.short.confirmed_step(baseline, noise) {''')
dest.write_text(s)
