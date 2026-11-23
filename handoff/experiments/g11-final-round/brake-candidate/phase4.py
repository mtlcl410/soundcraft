from pathlib import Path
import sys
c=Path('../brake-candidate')
p=c/'crates/playback/src/clock_follow.rs';s=p.read_text()
s=s.replace('tracking_pulses: u8,','tracking_pulses: u8,\n    stable_after_step:u8,').replace('tracking_pulses: 0,','tracking_pulses: 0,\n            stable_after_step:0,')
s=s.replace('fn phase_tracking(&self) -> bool { self.tracking_pulses','fn phase_tracking(&self) -> bool { self.stable_after_step==0 && self.state==State::Locked && self.tracking_pulses').replace('self.tracking_pulses=self.tracking_pulses.saturating_sub(1);', 'self.stable_after_step=self.stable_after_step.saturating_sub(1);self.tracking_pulses=self.tracking_pulses.saturating_sub(1);')
s=s.replace('self.step_pulses_left = 24;', 'self.stable_after_step=72;self.tracking_pulses=0;self.step_pulses_left = 24;')
s=s.replace('0 if self.phase_tracking() => at,','0 if self.phase_tracking() => at.saturating_sub(2600),')
p.write_text(s)
