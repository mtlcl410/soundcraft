s=s.replace('pub phase_grid_bpm: Option<f64>,', 'pub phase_grid_bpm: Option<f64>, pub control_bpm:Option<f64>,')
s=s.replace('    fn bpm(&self)', '''    fn control_bpm(&self)->Option<f64> {
        let fit=self.steady.period_us().or_else(||self.short.period_us());
        let fit=if self.phase_tracking() && self.settling.jitter_us()<950. {self.settling.period_us().or(fit)} else {fit};
        let period=match self.brake_pulses_left {0=>fit,1..=36=> self.short.period_us().or(fit), _=>self.last_wire_interval.map(|p|p as f64).or(fit)}?;
        (2_500. ..=502_000.).contains(&period).then(||2_500_000./period.clamp(2_500.,500_000.))
    }
    fn bpm(&self)''').replace('brake_grid_bpm: self.brake_grid_bpm(),','brake_grid_bpm: self.brake_grid_bpm(),control_bpm:self.control_bpm(),').replace('s.phase_grid_bpm).or(s.bpm)','s.phase_grid_bpm).or(s.control_bpm).or(s.bpm)')
s=s.replace('self.steady.is_tempo_ramp() && self.settling.jitter_us()>900. && self.nudge_readout_pulses==0', 'self.steady.is_tempo_ramp() && self.short.jitter_us()>800. && self.settling.jitter_us()>1000. && self.nudge_readout_pulses==0')
