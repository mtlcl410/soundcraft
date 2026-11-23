from pathlib import Path
def transform(s):
    s=s.replace('    pub packed_delivery: bool,','    pub packed_delivery: bool,\n    pub wire_phase_pending: bool,')
    hook='            packed_delivery: self.packed_delivery,'
    s=s.replace(hook,hook+'''
            wire_phase_pending: {
                let [a,b,c] = [self.wire_stamps[10], self.wire_stamps[11], self.wire_stamps[12]];
                let gap = c.saturating_sub(b);
                let last = b.saturating_sub(a);
                if self.packed_delivery {
                    self.steady.period_us().is_none()
                } else {
                    self.wire_points >= 3 && (gap <= 1000 || (last >= 2500 && gap > last + last / 2))
                }
            },''')
    s=s.replace('            self.singleton_groups = 0;\n            self.short.clear();','            self.singleton_groups = 0;\n            self.settling.clear();\n            self.readout_pulses_left = 0;\n            self.short.clear();')
    s=s.replace('    let Some(bpm) = s.brake_grid_bpm', '    if s.wire_phase_pending { return false; }\n    let Some(bpm) = s.brake_grid_bpm')
    return s
s=transform(s)

