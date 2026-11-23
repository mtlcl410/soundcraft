from pathlib import Path
d=Path(__file__).resolve().parent
for n in ['beat','mtc','follow']:
 p=d/n/'crates/playback/src'
 f=p/'beat_clock.rs';s=f.read_text()
 block='''            if let Some(window) = self.repayment {
                return Some(self.repay(window, b, now, s, send));
            }
'''
 s=s.replace(block,''); pos=s.index('            if let Some(last) = self.last_sent',s.index('fn update('));s=s[:pos]+block+s[pos:];f.write_bytes(s.encode())
 f=p/'beat_clock/recovery.rs';s=f.read_text().replace('        if now < due {\n            return due;','''        // Preserve wire spacing when the worker wakes late. At fast tempos the
        // planned spacing itself can be shorter than the ordinary catch-up floor.
        let period_samples = (window.end_sample - window.start_sample) as f64 / (window.last_pulse - window.first_owed) as f64;
        let spacing = Duration::from_secs_f64(period_samples / b.samples_per_second).min(CATCH_UP_SPACING);
        let earliest = self.last_sent.map_or(due, |last| due.max(last + spacing));
        if now < earliest {
            return earliest;''');f.write_bytes(s.encode())
