exec((d/'r2-pending.py').read_text(encoding='utf-8-sig'))
s=s.replace('State::Locked if self.brake_pulses_left > 0 || self.phase_tracking() || self.packed_delivery', 'State::Locked if self.step_pulses_left > 0 || self.brake_pulses_left > 0 || self.phase_tracking() || self.packed_delivery')
