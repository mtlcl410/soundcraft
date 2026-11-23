from pathlib import Path
d=Path(__file__).resolve().parent
for n in ['beat','mtc','follow']:
 p=d/n/'crates/playback/src'
 f=p/'beat_clock.rs';s=f.read_text()
 s=s.replace('const TICKS_PER_CLOCK:', 'mod recovery;\nuse recovery::Repayment;\n\nconst TICKS_PER_CLOCK:')
 s=s.replace('    remap: bool,','    remap: bool,\n    timing_interrupted: bool,\n    repayment: Option<Repayment>,',1)
 s=s.replace('        // A receiver missed pulses. Reposition it using SPP before sending fresh clocks.\n        self.remap |= self.last_position.is_some();','        self.timing_interrupted = self.last_position.is_some();')
 a=s.index('        if self.pass == Some(b.pass)',s.index('fn update('))
 b=s.index('        let mut clock = false;',a)
 s=s[:a]+'''        let interrupted = std::mem::take(&mut self.timing_interrupted);
        if self.pass == Some(b.pass) && b.playing && !remap {
            if interrupted {
                self.repayment = Repayment::new(self.next_pulse, at, s);
            }
            if let Some(last) = self.last_sent
                && now < last + CATCH_UP_SPACING
            {
                return Some(last + CATCH_UP_SPACING);
            }
            if let Some(window) = self.repayment {
                return Some(self.repay(window, b, now, s, send));
            }
        } else {
            self.repayment = None;
        }
'''+s[b:]
 f.write_bytes(s.encode());g=p/'beat_clock/recovery.rs';g.parent.mkdir(exist_ok=True);g.write_bytes((d/'repayment.rs').read_text(encoding='utf-8-sig').encode())
