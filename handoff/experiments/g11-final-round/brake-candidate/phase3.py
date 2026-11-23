from pathlib import Path
import sys
c=Path('../brake-candidate')
p=c/'crates/playback/src/clock_follow.rs';s=p.read_text()
s=s.replace('if self.brake_pulses_left > 0 || self.phase_tracking()', 'if self.brake_pulses_left > 0')
s=s.replace('0 if self.phase_tracking() => at,','0 if self.phase_tracking() => self.short.predict_us(self.fit_index).map_or(at,|sh|(at+sh)/2),')
s=s.replace('self.step_pulses_left = 24;', 'self.tracking_pulses=0;self.step_pulses_left = 24;').replace('fn phase_tracking(&self) -> bool { self.tracking_pulses','fn phase_tracking(&self) -> bool { self.state==State::Locked && self.tracking_pulses')
p.write_text(s)
