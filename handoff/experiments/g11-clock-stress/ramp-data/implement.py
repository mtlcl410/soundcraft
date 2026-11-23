from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress')
w=d/'ramps';q=w/'crates/ui-egui/src/app/clock_follow/tests/ramp_response.rs';q.write_text((d/'ramp-data/ramp-test.rs').read_text())
p=w/'crates/playback/src/sync_input.rs';s=p.read_text();key='    pub fn period_us(&self) -> Option<f64> {'
s=s.replace(key,'''    /// Detect sustained tempo motion without changing the stable linear period/phase estimates.
    /// With evenly spaced pulse indices, the centred quadratic is orthogonal to both a constant
    /// and a linear slope. A constant-speed clock therefore contributes no curvature.
    pub(crate) fn is_tempo_ramp(&self) -> bool {
        if self.len < 24 || self.slope <= 0. {
            return false;
        }
        let Some((last, stamp)) = self.last else {return false};
        let first = (self.cursor + N - self.len) % N;
        if last.saturating_sub(self.points[first].0) != self.len as i64 - 1 {
            return false;
        }
        let n = self.len as f64;
        let center = (n - 1.) / 2.;
        let variance = (n*n - 1.) / 12.;
        let norm = n*(n*n-1.)*(n*n-4.)/180.;
        let projection = self.points[..self.len].iter().map(|&(i,t)| {
            let x=i.saturating_sub(last) as f64 + center;
            (x*x - variance) * t.saturating_sub(stamp) as f64
        }).sum::<f64>().abs();
        // Reject stationary timestamp noise (three standard errors) and slow clock flutter.
        // Twice the quadratic coefficient is the change in pulse period per pulse.
        projection > 3. * self.jitter * norm.sqrt()
            && 2. * projection / norm > 0.00045 * self.slope * self.slope / 1_000_000.
    }

'''+key);p.write_text(s)
p=w/'crates/playback/src/clock_follow.rs';s=p.read_text().replace('    pub jitter_us: f64,','    /// The source has a sustained tempo trend above its measured timestamp noise.\n    pub tempo_ramp: bool,\n    pub jitter_us: f64,').replace('            jitter_us: self.steady.jitter_us(),','            tempo_ramp: self.state == State::Locked && self.step_pulses_left == 0 && self.steady.is_tempo_ramp(),\n            jitter_us: self.steady.jitter_us(),');p.write_text(s)
p=w/'crates/ui-egui/src/app/clock_follow.rs';s=p.read_text().replace('let spacing = if s.recovering_tempo_step { 2 }', 'let spacing = if s.recovering_tempo_step || s.tempo_ramp { 2 }').replace('if (slope - bpm).abs() < 0.15 && phase.abs() < 0.003 {','// Follow a sustained pitch-fader move more closely while preserving the\n    // noise-filtered wire period and phase in both modes.\n    let (bpm_deadband, phase_deadband) = if s.tempo_ramp { (0.035, 0.0005) } else { (0.15, 0.003) };\n    if (slope - bpm).abs() < bpm_deadband && phase.abs() < phase_deadband {').replace('let recovery_beats = if phase.abs() <= 0.006 { 8. }','let recovery_beats = if s.tempo_ramp {0.6} else if phase.abs() <= 0.006 { 8. }').replace('(slope - target).abs() >= 0.15','(slope - target).abs() >= bpm_deadband');p.write_text(s)
p=q;s=p.read_text().replace('let mut signed=Vec::new();','let mut signed=Vec::new(); let mut ramp_pulses=0;').replace('                if i%12==0','                ramp_pulses+=usize::from(snap.tempo_ramp);\n                if i%12==0').replace('false_steps={steps} locked_jump=', 'false_steps={steps} adaptive={ramp_pulses} locked_jump=').replace('peak<=4. && steps==0 && jump<=0.1','peak<=4. && steps==0 && jump<=0.1 && (delta.abs()>1. || ramp_pulses==0)');p.write_text(s)

