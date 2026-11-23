from pathlib import Path
import sys
c=Path('../brake-candidate')
p=c/'crates/playback/src/clock_follow.rs';s=p.read_text()
s=s.replace('let a=self.last_wire_interval?;', 'let a=self.last_wire_interval?;').replace('else {self.short.period_us()}','else {let w=&self.wire_stamps;Some((w[12]-w[8]) as f64 / 4.)}')
s=s.replace('self.step_pulses_left = 24;', 'self.tracking_pulses=0;self.step_pulses_left = 24;').replace('fn phase_tracking(&self) -> bool { self.tracking_pulses','fn phase_tracking(&self) -> bool { self.state==State::Locked && self.tracking_pulses')
s=s.replace('recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0 || self.phase_tracking(),','recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0,')
s=s.replace('self.step_pulses_left = 0;','self.step_pulses_left = 0; self.tracking_pulses = 0;')
p.write_text(s)
p=c/'crates/ui-egui/src/app/clock_follow.rs';s=p.read_text();a=s.index('fn update_grid(');b=s.index('#[cfg(test)]',a);v=s[a:b]
v=v.replace('s.recovering_tempo_step','(s.recovering_tempo_step || s.phase_grid_bpm.is_some())').replace('let spacing = if (s.recovering_tempo_step', 'let spacing = if s.phase_grid_bpm.is_some() { 0 } else if (s.recovering_tempo_step')
v=v.replace('let bpm_deadband','let bpm_deadband').replace('let (bpm_deadband, phase_deadband) = if (s.recovering','let (bpm_deadband, phase_deadband) = if s.phase_grid_bpm.is_some() {(0.02,0.0003)} else if (s.recovering')
p.write_text(s[:a]+v+s[b:])
