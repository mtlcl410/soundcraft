from pathlib import Path
import sys
src=Path(sys.argv[1])/'crates/playback/src'
p=src/'mtc_input.rs'
s=p.read_text(encoding='utf8')
def swap(old,new):
 global s
 assert s.count(old)==1, old[:150]
 s=s.replace(old,new)
swap('''        let at_midnight = Timecode { negative: false, hours: 24, minutes: 0, seconds: 0, frames: 0 }.to_frames(self.rate);
        Self { quarter: (self.quarter + quarters) % (at_midnight * 4), ..self }''','''        Self { quarter: self.quarter.saturating_add(quarters), ..self }
    }

    fn quarters_per_day(self) -> i64 {
        Timecode { negative: false, hours: 24, minutes: 0, seconds: 0, frames: 0 }.to_frames(self.rate) * 4
    }

    // Wire hours wrap at midnight. A neighbouring group or locate (up to two frames)
    // carries the day forward or back. A non-contiguous explicit locate starts on day zero.
    fn on_reader_day(self, previous: Option<Self>, explicit_locate: bool) -> Self {
        let Some(last) = previous.filter(|p| p.rate == self.rate) else { return self };
        let day = self.quarters_per_day();
        let delta = self.quarter - last.quarter.rem_euclid(day);
        let nearest = (delta + day / 2).rem_euclid(day) - day / 2;
        if nearest.abs() <= 8 {
            last.advance(nearest)
        } else if explicit_locate {
            self
        } else {
            last.advance(delta)
        }''')
swap('Timecode::from_frames(self.quarter / 4, self.rate).format(self.rate)','Timecode::from_frames(self.quarter.rem_euclid(self.quarters_per_day()) / 4, self.rate).format(self.rate)')
swap('#[derive(Default)]\npub(crate) struct Reader {','''/// A quarter-frame pair or a universal full-frame SysEx can span input callbacks.
/// System Real-Time bytes have no effect on the message being assembled.
#[derive(Default)]
struct WireMessage {
    bytes: [u8; 10],
    len: usize,
}

impl WireMessage {
    fn push(&mut self, byte: u8) -> Option<&[u8]> {
        match byte {
            0xfc => return Some(&[0xfc]),
            0xf8..=0xff => {}
            0xf0 | 0xf1 => {
                self.bytes[0] = byte;
                self.len = 1;
            }
            0xf7 if self.len == 9 && self.bytes[0] == 0xf0 => {
                self.bytes[9] = byte;
                self.len = 0;
                return Some(&self.bytes);
            }
            0x80..=0xf7 => self.len = 0,
            _ if self.len == 1 && self.bytes[0] == 0xf1 => {
                self.bytes[1] = byte;
                self.len = 0;
                return Some(&self.bytes[..2]);
            }
            _ if (1..9).contains(&self.len) => {
                self.bytes[self.len] = byte;
                self.len += 1;
            }
            _ => self.len = 0,
        }
        None
    }
}

#[derive(Default)]
pub(crate) struct Reader {
    wire: WireMessage,''')
swap('        self.source = source;\n        self.next = 0;', '        self.source = source;\n        self.wire.len = 0;\n        self.next = 0;')
swap('''        self.read(bytes, stamp);
        let delay''','''        let mut received = false;
        let mut stopped = false;
        // A transport Stop resets the chase state but must preserve the surrounding
        // wire message while this callback (or a later one) finishes it.
        let mut wire = std::mem::take(&mut self.wire);
        for &byte in bytes {
            if let Some(message) = wire.push(byte) {
                received = true;
                stopped |= message == [0xfc];
                self.read_message(message, stamp);
            }
        }
        self.wire = wire;
        if !received {return false;}
        let delay''')
swap('''            || (bytes == [0xfc] && had_transport)
            || (bytes.first() == Some(&0xf0) && self.located_start.is_some() && located != self.located_start)''','''            || (stopped && had_transport)
            || (self.located_start.is_some() && located != self.located_start)''')
swap('''    pub(crate) fn read(&mut self, bytes: &[u8], now: i64) {
        self.expire(now);''','''    #[cfg(test)]
    pub(crate) fn read(&mut self, bytes: &[u8], now: i64) {
        self.receive(bytes, now, now);
    }

    fn read_message(&mut self, bytes: &[u8], now: i64) {
        self.expire(now);''')
swap('''                if let Some(position) = Position::decode(h, m, s, f) {
                    self.reset(self.source);''','''                if let Some(position) = Position::decode(h, m, s, f) {
                    let position = position.on_reader_day(self.incoming, true);
                    self.reset(self.source);''')
swap('''                    self.incoming = Some(position);
                    if let Some(last) = self.previous {''','''                    let position = position.on_reader_day(self.previous.or(self.located_start), false);
                    self.incoming = Some(position);
                    if let Some(last) = self.previous {''')
swap('''            assert_eq!(reader.take(0), Some(ChaseEvent::Roll(Position { quarter: 7, rate }, 0)));''','''            let midnight = Timecode { negative: false, hours: 24, minutes: 0, seconds: 0, frames: 0 }.to_frames(rate);
            assert_eq!(reader.take(0), Some(ChaseEvent::Roll(Position { quarter: midnight * 4 + 7, rate }, 0)));''')
p.write_text(s,encoding='utf8')
p=src/'midi.rs';s=p.read_text(encoding='utf8')
swap('''        if matches!(bytes.first(), Some(0xf0 | 0xf1 | 0xfc)) {
            let arrival = self.now();''','''        // The selected MTC reader frames messages across callbacks and ignores interleaved
        // real-time bytes. Channel recording still handles the original port message below.
        if self.mtc_online() {
            let arrival = self.now();''')
swap('''                self.wake_mtc_host();
            }
            return;
        }
        let Some(&status)''','''                self.wake_mtc_host();
            }
        }
        let Some(&status)''')
p.write_text(s,encoding='utf8')
