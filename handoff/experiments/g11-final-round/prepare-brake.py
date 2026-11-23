from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'crates/playback/src/clock_follow.rs'
s=p.read_text(encoding='utf-8')
def sub(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a))
 s=s.replace(a,b)
sub("    latest: Option<i64>,","""    latest: Option<i64>,
    // Wire history survives Coast. A fresh pair in the new acquisition epoch
    // replaces the old period; the silence between epochs is never a beat.
    last_wire_interval: Option<i64>,
    previous_wire_interval: Option<i64>,
    brake_pulses_left: u8,
    last_sensing_byte: Option<i64>,""")
sub("            latest: None,","""            latest: None,
            last_wire_interval: None,
            previous_wire_interval: None,
            brake_pulses_left: 0,
            last_sensing_byte: None,""")
sub("            State::Locked =>", """            State::Locked if self.brake_pulses_left > 0 => Some(self.played_pulse),
            State::Locked =>""")
sub("            || self.step_pulses_left != 0","            || self.step_pulses_left != 0\n            || self.brake_pulses_left != 0")
sub("        self.steady.period_us().or_else(|| self.short.period_us()).filter(|p| (2500. ..=500_000.).contains(p)).map(|p| 2_500_000. / p)","""        let fit = self.steady.period_us().or_else(|| self.short.period_us());
        let period = if self.brake_pulses_left > 0 { self.last_wire_interval.map(|p| p as f64).or(fit) } else { fit }?;
        // Timestamp jitter at either tempo boundary must not invalidate a legal source.
        (2_450. ..=502_000.).contains(&period).then(|| 2_500_000. / period.clamp(2_500., 500_000.))""")
sub("    pub recovering_tempo_step: bool,","""    pub recovering_tempo_step: bool,
    /// A fast brake has reached long pulse intervals. Follow the arriving pulses
    /// themselves while the new tempo and phase settle.
    pub braking: bool,""")
sub("            recovering_tempo_step: self.step_pulses_left > 0,","""            recovering_tempo_step: self.step_pulses_left > 0 || self.brake_pulses_left > 0,
            braking: self.brake_pulses_left > 0,""")
a=s.index('        let period = self.bpm().map_or(0.,')
b=s.index('            // Idle pulses',a)
s=s[:a]+'''        let period = self.bpm().map(|bpm| 2_500_000. / bpm);
        // The first pulse of an acquisition has no interval yet. Give even a
        // 5 BPM source time to provide a second pulse, also when returning from Coast.
        let timeout = match (period, self.last_wire_interval) {
            (None, _) if self.short.period_us().is_none() && self.steady.period_us().is_none() => 1_500_000,
            (fitted, interval) => {
                let last = interval.unwrap_or(0);
                let growth = if self.brake_pulses_left > 0 {
                    last.saturating_sub(self.previous_wire_interval.unwrap_or(last)).max(0)
                } else { 0 };
                let expected = fitted.unwrap_or(0.).max(last.saturating_add(growth) as f64);
                // Timestamped groups of up to five pulses can be followed by
                // a whole group's silence even when the preceding group was short.
                let group_gap = if self.packed_delivery { 5. * fitted.unwrap_or(0.) + 1000. } else { 0. };
                (3. * expected).max(group_gap).ceil().clamp(150_000., 1_500_000.) as i64
            }
        };
        let cable_lost = self.last_sensing_byte.is_some_and(|last| now.saturating_sub(last) > 300_000);
        if cable_lost { self.last_sensing_byte = None; }
        if self.latest.is_some_and(|last| cable_lost || now.saturating_sub(last) > timeout) {
''' + s[b:]
sub("        self.step_intervals = 0;\n        self.changes = 0;","        self.step_intervals = 0;\n        self.brake_pulses_left = 0;\n        self.changes = 0;")
sub("        self.latest = Some(at);","""        self.brake_pulses_left = self.brake_pulses_left.saturating_sub(1);
        if let Some(prev) = self.latest {
            let gap = at.saturating_sub(prev).min(1_500_000);
            if !self.packed_delivery && gap > 1000 {
                if let (Some(last), Some(before)) = (self.last_wire_interval, self.previous_wire_interval) {
                    // A sustained widening of intervals into slow-clock territory
                    // distinguishes a brake from ordinary jitter or a small tempo step.
                    if gap > 40_000 && gap > last + last / 12 && last > before + before / 12 {
                        self.brake_pulses_left = 48;
                    } else if self.brake_pulses_left > 0 && gap.abs_diff(last) > (last / 16) as u64 {
                        self.brake_pulses_left = 48;
                    }
                }
                self.previous_wire_interval = self.last_wire_interval;
                self.last_wire_interval = Some(gap);
            }
        }
        self.latest = Some(at);""")
sub("            self.played_stamp = self.steady.predict_us(self.fit_index).unwrap_or(at);","            self.played_stamp = if self.brake_pulses_left > 0 { at } else { self.steady.predict_us(self.fit_index).unwrap_or(at) };")
sub("        for &byte in bytes {","""        if !bytes.is_empty() && (self.last_sensing_byte.is_some() || bytes.contains(&0xfe)) {
            self.last_sensing_byte = Some(self.last_sensing_byte.map_or(at, |last| last.max(at)));
        }
        for &byte in bytes {""")
p.write_text(s,encoding='utf-8')
p=root/'crates/ui-egui/src/app/clock_follow.rs'
s=p.read_text(encoding='utf-8').replace('render_until > 0 && s.packed_delivery && s.recovering_tempo_step','render_until > 0 && (s.packed_delivery || s.braking) && s.recovering_tempo_step')
p.write_text(s,encoding='utf-8')
p=root/'crates/playback/src/clock_follow/tests.rs'
s=p.read_text(encoding='utf-8')
sub('        let mut r = Follower { coast, ..Follower::default() };\n        feed(&mut r, 0xfa, 0);', '        let mut r = Follower { coast, ..Follower::default() };\n        feed(&mut r, 0xf8, -40_000);\n        feed(&mut r, 0xf8, -20_000);\n        feed(&mut r, 0xfa, 0);')
p.write_text(s,encoding='utf-8')



