from pathlib import Path
p=Path('crates/playback/src/clock_follow.rs')
s=p.read_text()
s=s.replace('    pub phase_grid_bpm:','    /// Short-term slope for upcoming score events while tracking a measured phase excursion.\n    pub phase_grid_bpm:')
s=s.replace('    settling: PulseFit<49>,','    // Two beats and their shared endpoint. Let measured BPM settle after a temporary nudge.\n    settling: PulseFit<49>,').replace('    tracking_pulses: u8,','    phase_pulses_left: u8,').replace('tracking_pulses','phase_pulses_left')
a=s.index('    fn phase_period');b=s.index('    fn bpm(',a)
s=s[:a]+'''    fn phase_period(&self) -> Option<f64> {
        let last = self.last_wire_interval?;
        let prior = self.previous_wire_interval?;
        if last.abs_diff(prior) <= 2 && last >= 2_500 {
            // An ideal source may round two successive intervals in opposite directions.
            return Some((last + prior) as f64 / 2.);
        }
        let recent = self.wire_stamps[12].saturating_sub(self.wire_stamps[8]) as f64 / 4.;
        if self.steady.period_us().is_some_and(|period| (recent - period).abs() > 0.05 * period) {
            Some(recent)
        } else {
            self.short.period_us()
        }
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
        let phase_changed = noise < 1_000. && self.steady.predict_us(self.fit_index.saturating_add(1))
            .is_some_and(|expected| at.abs_diff(expected) as f64 > (3. * noise).max(350.));
        if interval_changed || phase_changed {
            // A deck can bend its speed below the eight-percent step threshold.
            // Stop committing ahead of the wire while the latest phase is moving.
            self.phase_pulses_left = 48;
        }
    }
'''+s[b:]
a=s.index('        self.phase_pulses_left=self.phase_pulses_left.saturating_sub(1);');b=s.index('        self.observe_wire_interval(at);',a);s=s[:a]+'        self.observe_phase_arrival(at);\n'+s[b:]
s=s.replace('recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0 || self.phase_tracking(),','recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0,')
s=s.replace('Some(sh),Some(lo)','Some(short_phase),Some(steady_phase)').replace('sh.abs_diff(lo)','short_phase.abs_diff(steady_phase)')
s=s.replace('            self.cue = None;\n            self.step_pulses_left = 0;','            self.cue = None;\n            self.step_pulses_left = 0;\n            self.phase_pulses_left = 0;')
p.write_text(s)
p=Path('crates/ui-egui/src/app/clock_follow.rs');s=p.read_text().replace('let correcting=s.recovering_tempo_step || precise;', 'let tracking = s.phase_grid_bpm.is_some();\n    let correcting = s.recovering_tempo_step || tracking || precise;')
a=s.index('    let precise=');b=s.index('    let before = grid.tempos()',a)
s=s[:a]+'''    if s.state != State::Locked || s.pulse <= origin {
        return false;
    }
    // With a clean source, reach the next pulse when measured grid phase drifts out
    // of tolerance. Retain the wider jitter deadband for noisy and batched delivery.
    let precise = !s.packed_delivery && !s.braking && s.jitter_us < 1_400. && phase.abs() > 0.0012;
    let tracking = s.phase_grid_bpm.is_some();
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
'''+s[b:]
s=s.replace('let spacing = if precise || s.phase_grid_bpm.is_some()', 'let spacing = if precise || tracking')
s=s.replace('if s.state != State::Locked || s.pulse <= origin || (!tempo_step && since_edit < spacing * TICKS_PER_PULSE)', 'if !tempo_step && since_edit < spacing * TICKS_PER_PULSE')
s=s.replace('        let join = ((ahead / TICKS_PER_PULSE as f64 + if s.phase_grid_bpm.is_some() {0.30} else {1.0}).ceil() as i64).saturating_mul(TICKS_PER_PULSE);','''        // On a low-noise nudge, retain at least 30% of an interval for the bridge.
        // A larger correction has a full pulse of headroom.
        let headroom = if tracking { 0.30 } else { 1. };
        let join = ((ahead / TICKS_PER_PULSE as f64 + headroom).ceil() as i64).saturating_mul(TICKS_PER_PULSE);''')
s=s.replace('        if grid.set_tempo(edit, bridge.clamp(5., 1000.)).is_ok() {','''        if tracking || precise {
            // A replacement bridge starts after committed audio. Only its old future
            // join can overlap the revised slope.
            while let Some(tick) = grid.tempos().last().map(|event| event.tick).filter(|t| *t > edit) {
                grid.remove_tempo(tick);
            }
        }
        if grid.set_tempo(edit, bridge.clamp(5., 1000.)).is_ok() {''')
p.write_text(s)
