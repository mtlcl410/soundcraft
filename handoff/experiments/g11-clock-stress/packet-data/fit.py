from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress')
def edit(p,a,b):
 s=p.read_text(encoding='utf8');assert a in s,a;p.write_text(s.replace(a,b),encoding='utf8')
p=d/'packets/crates/playback/src/clock_follow.rs'
edit(p,'    fit_index: i64,','''    fit_index: i64,
    // Three F8s within one millisecond cannot be individual beats in the
    // supported tempo range. Keep every pulse, but fit only batch heads.
    packet_head: Option<(i64, i64)>,
    packed_delivery: bool,''')
edit(p,'            fit_index: 0,','''            fit_index: 0,
            packet_head: None,
            packed_delivery: false,''')
edit(p,'        self.latest = None;','''        self.latest = None;
        self.packet_head = None;
        self.packed_delivery = false;
        self.step_intervals = 0;''')
edit(p,'        let timeout = self.bpm().map_or(150_000, |bpm| (7_500_000. / bpm).ceil() as i64).max(150_000);','''        let period = self.bpm().map_or(0., |bpm| 2_500_000. / bpm);
        let mut timeout = (3. * period).ceil().max(150_000.) as i64;
        if self.packed_delivery && let Some((head, _)) = self.packet_head {
            // Some of the upcoming silence was already delivered in this batch.
            timeout = timeout.saturating_add(((self.fit_index - head) as f64 * period).round() as i64);
        }''')
a='''        self.short.push(self.fit_index, at);
        // Long regression'''
b='''        if self.packet_head.is_none_or(|(_, stamp)| at.saturating_sub(stamp) > 1000) {
            self.packet_head = Some((self.fit_index, at));
        }
        let (head, stamp) = self.packet_head.unwrap_or((self.fit_index, at));
        if !self.packed_delivery && self.fit_index - head >= 2 {
            self.packed_delivery = true;
            self.short.clear();
            self.steady.clear();
            self.short.push(head, stamp);
            self.steady.push(head, stamp);
            self.changes = 0;
        }
        if !self.packed_delivery || self.fit_index == head {
            self.observe_period(at);
        }
        let start_requested = self.awaiting_clock.take().is_some();'''
s=p.read_text(encoding='utf8');i=s.index(a);j=s.index('        let start_requested = self.awaiting_clock.take().is_some();',i);k=s.index('    /// System common bytes',j)
est=s[i:j];s=s[:i]+b+s[j+len('        let start_requested = self.awaiting_clock.take().is_some();'):k]+'    fn observe_period(&mut self, at:i64) {\n'+est+'    }\n'+s[k:];p.write_text(s,encoding='utf8')
edit(p,'if let Some((index, stamp)) = self.short.confirmed_step_start','if let Some(((index, stamp), intervals)) = self.short.confirmed_step_start')
edit(p,'self.step_intervals = (self.fit_index - index) as u8;','self.step_intervals = intervals;')
p=d/'packets/crates/playback/src/sync_input.rs'
edit(p,'pub fn confirmed_step_start(&self, previous: f64, noise_us: f64) -> Option<(i64, i64)> {','pub fn confirmed_step_start(&self, previous: f64, noise_us: f64) -> Option<((i64, i64),u8)> {')
edit(p,'self.step_intervals(previous, 2, 0.30, noise_us * 8., 0.03).or_else(|| self.step_intervals(previous, 4, 0.08, noise_us * 2., 0.4))','self.step_intervals(previous, 2, 0.30, noise_us * 8., 0.03).map(|head| (head,2)).or_else(|| self.step_intervals(previous, 4, 0.08, noise_us * 2., 0.4).map(|head|(head,4)))')
edit(p,'let (_, end) = self.last?;\n        let period = end.saturating_sub(start.1) as f64 / count as f64;','let (index, end) = self.last?;\n        let pulses = (index - start.0) as f64;\n        let period = end.saturating_sub(start.1) as f64 / pulses;')
edit(p,'if period <= 0. || change.abs() + 1. / (count as f64)','if !(2500. ..=500_000.).contains(&period) || change.abs() + 1. / pulses')
edit(p,'let interval = self.points[(first + i + 1) % N].1.saturating_sub(self.points[(first + i) % N].1) as f64;','let (a, start) = self.points[(first+i)%N];\n            let (b,end) = self.points[(first+i+1)%N];\n            let interval = end.saturating_sub(start) as f64 / (b-a) as f64;')

