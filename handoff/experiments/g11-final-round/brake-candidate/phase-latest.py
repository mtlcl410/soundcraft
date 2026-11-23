from pathlib import Path
c=Path('../brake-candidate')
p=c/'crates/playback/src/clock_follow.rs';s=Path('crates/playback/src/clock_follow.rs').read_text(encoding='utf-8')
def rep(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
rep('    pub brake_grid_bpm: Option<f64>,','    pub brake_grid_bpm: Option<f64>,\n    pub phase_grid_bpm: Option<f64>,')
rep('    short: PulseFit<12>,','    settling: PulseFit<49>,\n    tracking_pulses: u8,\n    short: PulseFit<12>,')
rep('            short: Default::default(),','            settling: Default::default(),\n            tracking_pulses: 0,\n            short: Default::default(),')
rep('State::Locked if self.brake_pulses_left > 0','State::Locked if self.brake_pulses_left > 0 || self.phase_tracking()')
rep('            || self.brake_pulses_left != 0','            || self.brake_pulses_left != 0\n            || self.phase_tracking()')
rep('    fn bpm(&self) -> Option<f64> {','''    fn phase_tracking(&self) -> bool { self.tracking_pulses > 0 && self.step_pulses_left == 0 && self.brake_pulses_left == 0 && !self.packed_delivery }
    fn phase_period(&self)->Option<f64>{
        let a=self.last_wire_interval?; let b=self.previous_wire_interval?;
        if a.abs_diff(b)<=2 && a>=2500 {Some((a+b) as f64/2.)} else {self.short.period_us()}
    }
    fn bpm(&self) -> Option<f64> {''')
rep('        let period = match self.brake_pulses_left {','''        let fit=if self.phase_tracking() && self.settling.jitter_us()<950. {
            self.settling.period_us().or(fit)
        } else {fit};
        let period = match self.brake_pulses_left {''')
rep('            brake_grid_bpm: self.brake_grid_bpm(),','''            brake_grid_bpm: self.brake_grid_bpm(),
            phase_grid_bpm: self.phase_tracking().then(|| self.phase_period()).flatten().map(|p|2_500_000./p),''')
rep('recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0,','recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0 || self.phase_tracking(),')
rep('        self.short.clear();\n        self.steady.clear();','        self.short.clear();\n        self.steady.clear();\n        self.settling.clear();\n        self.tracking_pulses=0;')
rep('        self.observe_wire_interval(at);','''        self.tracking_pulses=self.tracking_pulses.saturating_sub(1);
        if !self.packed_delivery && self.wire_points==13 && self.step_pulses_left==0
            && let (Some(last),Some(period))=(self.latest,self.steady.period_us())
            && (at.saturating_sub(last) as f64 - period).abs() > (5.*self.steady.jitter_us()).max(0.012*period).max(30.) {
            self.tracking_pulses=48;
        }
        self.observe_wire_interval(at);''')
rep('                0 => self.steady.predict_us(self.fit_index).unwrap_or(at),','                0 if self.phase_tracking() => at,\n                0 => self.steady.predict_us(self.fit_index).unwrap_or(at),')
rep('        self.short.push(ordinal, at);','        self.settling.push(ordinal,at);\n        self.short.push(ordinal, at);')
rep('            if let Some(((index, stamp), intervals)) = step {','''            if !self.packed_delivery && self.step_pulses_left==0
                && let (Some(sh),Some(lo))=(self.short.predict_us(ordinal),self.steady.predict_us(ordinal))
                && (sh.abs_diff(lo) as f64>(3.*self.short.jitter_us()).max(950.) || self.short.jitter_us()<5. && (fast-slow).abs()>0.01*slow) {
                self.tracking_pulses=48;
            }
            if let Some(((index, stamp), intervals)) = step {''')
p.write_text(s,encoding='utf-8')
p=c/'crates/ui-egui/src/app/clock_follow.rs';s=Path('crates/ui-egui/src/app/clock_follow.rs').read_text(encoding='utf-8')
s=s.replace('s.brake_grid_bpm.or(s.bpm)','s.brake_grid_bpm.or(s.phase_grid_bpm).or(s.bpm)').replace('(s.packed_delivery || s.braking) && s.recovering','(s.packed_delivery || s.braking || s.phase_grid_bpm.is_some()) && s.recovering')
p.write_text(s,encoding='utf-8')