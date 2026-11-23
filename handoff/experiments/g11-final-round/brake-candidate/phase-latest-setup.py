from pathlib import Path
c=Path('../brake-candidate')
s=(c/'phase-setup.py').read_text()
s=s.replace('self.short.push(self.fit_index, at);','self.short.push(ordinal, at);').replace('self.settling.push(self.fit_index,at);','self.settling.push(ordinal,at);')
s=s.replace('if let Some(((index, stamp), intervals)) = self.short.confirmed_step(slow, noise) {','if let Some(((index, stamp), intervals)) = step {').replace('self.fit_index),self.steady.predict_us(self.fit_index)','ordinal),self.steady.predict_us(ordinal)')
s=s.replace("rep('                0 => self.steady.predict_us(self.fit_index).unwrap_or(at),','                0 if self.phase_tracking() => at,\\n                0 => self.steady.predict_us(self.fit_index).unwrap_or(at),')","rep('                0 if self.packed_delivery => at,','                0 if self.packed_delivery || self.phase_tracking() => at,')")
(c/'phase-latest.py').write_text(s)
d=(c/'pcm_probe.py').read_text();d=d.replace("'struct PreparedResume;\\n'","'struct PreparedResume;\\nmod wire_step{'+read('crates/playback/src/clock_follow/wire_step.rs')+'}\\n'")
(c/'pcm-latest.py').write_text(d)
