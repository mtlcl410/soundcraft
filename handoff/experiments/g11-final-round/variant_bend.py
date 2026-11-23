src=src.replace("self.phase_pulses_left > 0 && !self.steady.is_tempo_ramp()", "self.phase_pulses_left > 0 && !self.gentle_ramp()")
src=src.replace("fn phase_tracking(&self)", """fn gentle_ramp(&self) -> bool {
    self.steady.is_tempo_ramp() && self.steady.period_us().zip(self.settling.period_us()).is_some_and(|(s, f)| (s-f).abs() < 0.004*s)
}
fn phase_tracking(&self)""")
src=src.replace("let precise = !s.tempo_ramp && !s.packed_delivery", "let precise = (!s.tempo_ramp || s.phase_grid_bpm.is_some()) && !s.packed_delivery")
src=src.replace("phase.abs() > 0.0026", "phase.abs() > if s.phase_grid_bpm.is_none() && s.jitter_us < 1. { 0.0026 } else { 0.0012 }")
src=src.replace("settling: PulseFit<49>", "nudge_readout_pulses: u8, settling: PulseFit<49>").replace("settling: Default::default()", "nudge_readout_pulses: 0, settling: Default::default()")
src=src.replace("self.settling.push(ordinal, at);","""self.nudge_readout_pulses = self.nudge_readout_pulses.saturating_sub(1);
if self.settling.period_us().zip(self.steady.period_us()).is_some_and(|(f,s)| (s-f).abs() > 0.007*s) {
    self.nudge_readout_pulses=192;
}
self.settling.push(ordinal, at);""").replace("self.phase_tracking() && self.settling.jitter_us() < 950.", "self.nudge_readout_pulses > 0 && self.settling.jitter_us() < 950.")
