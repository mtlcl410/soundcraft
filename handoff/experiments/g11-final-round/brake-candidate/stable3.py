exec((c/'stable2.py').read_text())
a=s.index('    fn noisy_bend(');b=s.index('    fn phase_tracking(',a)
s=s[:a]+'''    fn noisy_bend(&self)->bool{
        self.noise_power>850.0*850.0 && self.nudge_readout_pulses==0 &&
        self.short.period_us().zip(self.steady.period_us()).is_some_and(|(short,long)|((short-long)/long).abs()<0.025)
    }
'''+s[b:]
s=s.replace('nudge_readout_pulses:u8,','noise_power:f64, nudge_readout_pulses:u8,').replace('nudge_readout_pulses:0,','noise_power:0., nudge_readout_pulses:0,')
s=s.replace('        self.previous_wire_interval = self.last_wire_interval;','''        if let Some(prior)=self.last_wire_interval {
            let high_pass=(gap-prior).clamp(-7000,7000) as f64;
            self.noise_power += 0.025*(high_pass*high_pass/6. - self.noise_power);
        }
        self.previous_wire_interval = self.last_wire_interval;''')
