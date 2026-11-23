from pathlib import Path
d=Path('../brake-candidate')
s=(d/'integrated.rs').read_text().replace('if self.braking_trend() || (self.brake_pulses_left > 0 && changing) {','''let settled_step=self.brake_pulses_left==0 && self.step_pulses_left>0 && self.steady.period_us().is_some_and(|p|(gap as f64-p).abs() <= (3.*self.steady.jitter_us()).max(0.08*p).max(2_000.));
        if (!settled_step && self.braking_trend()) || (self.brake_pulses_left > 0 && changing) {''')
s=s.replace('[(130., 80.), (120., 100.), (180., 60.), (100., 120.), (80., 130.), (60., 180.)]', '[(120., 100.)]').replace('for transition in [384, 396]','for transition in [396]').replace('[Delivery::Jitter(1000), Delivery::Jitter(2000), Delivery::VariableBurst]','[Delivery::Jitter(1000)]')
(d/'step-vs-brake.rs').write_text(s)
(d/'step-vs-brake.rsp').write_text((d/'integrated.rsp').read_text().replace('integrated.','step-vs-brake.'))
