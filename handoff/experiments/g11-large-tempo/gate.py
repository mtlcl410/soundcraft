from pathlib import Path
r=Path('work/crates')
def sub(f,a,b):
 s=f.read_text();assert a in s,(f,a);f.write_bytes(s.replace(a,b).encode())
f=r/'playback/src/clock_follow.rs'
sub(f,'    fn bpm(&self)', '''    pub(crate) fn render_through_pulse(&self) -> Option<i64> {
        (self.state == State::Locked).then(|| self.played_pulse.saturating_add(1))
    }

    fn bpm(&self)''')
f=r/'playback/src/midi.rs'
sub(f,'    clock_source: AtomicUsize,','    clock_source: AtomicUsize,\n    clock_render_pulse: AtomicI64,')
sub(f,'            clock_source: AtomicUsize::new(usize::MAX),','            clock_source: AtomicUsize::new(usize::MAX),\n            clock_render_pulse: AtomicI64::new(i64::MAX),')
sub(f,'            self.clock_source.store(port.', '            self.clock_render_pulse.store(i64::MAX, Ordering::Release);\n            self.clock_source.store(port.')
sub(f,'        input.expire(now);\n        while let Some(action)', '''        input.expire(now);
        self.clock_render_pulse.store(input.render_through_pulse().unwrap_or(i64::MAX), Ordering::Release);
        while let Some(action)''')
sub(f,'            let action = input.receive(bytes, at);','''            let action = input.receive(bytes, at);
            self.clock_render_pulse.store(input.render_through_pulse().unwrap_or(i64::MAX), Ordering::Release);''')
sub(f,'    pub(crate) fn arm_clock_resume(','''    /// Inclusive clip/click event horizon. Coasting has no external render limit.
    pub fn clock_render_tick(&self) -> Option<i64> {
        let pulse = self.clock_render_pulse.load(Ordering::Acquire);
        (pulse != i64::MAX).then(|| pulse.saturating_mul(soundcraft_time::TICKS_PER_QUARTER / 24))
    }

    pub(crate) fn arm_clock_resume(''')
f=r/'playback/src/callback.rs'
sub(f,'    chasing: bool,','    chasing: bool,\n    following_clock: bool,')
sub(f,'            chasing: false,','            chasing: false,\n            following_clock: false,')
sub(f,'        self.chasing = chasing;','        self.chasing = chasing;\n        self.following_clock = false;')
sub(f,'                    self.mix.start_midi_at(origin);','                    self.mix.start_midi_at(origin);\n                    self.following_clock = true;')
sub(f,'        self.mix.render(&self.session, self.pos, n, &mut self.pending);','''        let through = if self.playing && self.following_clock { self.midi.as_ref().and_then(|feed| feed.clock_render_tick()) } else { None };
        self.mix.render_with_clock_limit(&self.session, self.pos, n, &mut self.pending, through);''')
f=r/'mix/src/strip.rs'
sub(f,'    pub(crate) note_start: Samples,','    pub(crate) note_start: Samples,\n    pub(crate) score: Range,')
a='fn zero_buf(';sub(f,a,'''impl Block {
    /// A held event range can span more than one device block when Clock returns.
    /// Keep those events ordered within this block; voices still render at the device rate.
    pub(crate) fn score_offset(self, relative: Samples) -> usize {
        let length = self.score.end.saturating_sub(self.score.start);
        let offset = relative.max(0) as usize;
        if length > self.frames as i64 {
            ((offset as u128 * self.frames as u128) / length as u128) as usize
        } else {
            offset
        }
    }
}

'''+a)
if 'use soundcraft_time::Range;' not in f.read_text() and 'Range,' not in f.read_text().splitlines()[0:10]:
 sub(f,'pub(crate) score: Range,','pub(crate) score: soundcraft_time::Range,')
f=r/'mix/src/lib.rs'
sub(f,'    midi_origin: Option<Samples>,','''    midi_origin: Option<Samples>,
    held_score_from: Option<Samples>,
    click_tails: Vec<click::Tail>,''')
sub(f,'            midi_origin: None,','            midi_origin: None,\n            held_score_from: None,\n            click_tails: Vec::with_capacity(32),')
sub(f,'    pub fn reset(&mut self) {\n        self.midi_origin', '    pub fn reset(&mut self) {\n        self.held_score_from = None;\n        self.click_tails.clear();\n        self.midi_origin')
sub(f,'        let frames = frames.min(self.max_block);\n        self.begin_block', '''        self.render_with_clock_limit(s, pos, frames, out, None);
    }

    /// Render audio and live input continuously, but dispatch score events only through
    /// the inclusive wire tick. A later block consumes the retained range exactly once.
    pub fn render_with_clock_limit(&mut self, s: &Session, pos: Samples, frames: usize, out: &mut [Vec<f32>], through_tick: Option<i64>) {
        let frames = frames.min(self.max_block);
        self.begin_block''')
sub(f,'        let note_start = self.midi_origin.unwrap_or(pos);','''        let physical_end = pos.saturating_add(frames as i64);
        let start = self.held_score_from.take().unwrap_or(pos);
        let limit = through_tick.map_or(physical_end, |t| s.tempo.tick_to_samples(t, s.sample_rate).saturating_add(1));
        let score = Range { start, end: physical_end.min(limit).max(start) };
        if !self.monitor_only && score.end < physical_end {
            self.held_score_from = Some(score.end);
        }
        let note_start = self.midi_origin.unwrap_or(start);''')
sub(f,'&& note_start < pos.saturating_add(frames as i64)', '&& note_start < score.end')
sub(f,'Block { pos, frames, note_start, any_solo:', 'Block { pos, frames, note_start, score, any_solo:')
sub(f,'            click::render(s, pos, frames, &mut self.main);','''            click::render(s, blk, &mut self.main, &mut self.click_tails);
        } else {
            self.click_tails.clear();''')
f=r/'mix/src/midi.rs'
sub(f,'    if blk.frames == 0 {','    if blk.frames == 0 || blk.score.start == blk.score.end {')
sub(f,'let pos = blk.pos.saturating_sub(offset);\n    let end = pos.saturating_add(blk.frames as i64);','let pos = blk.score.start.saturating_sub(offset);\n    let end = blk.score.end.saturating_sub(offset);')
sub(f,'usize::try_from(on.saturating_sub(pos)).unwrap_or(0)','blk.score_offset(on.saturating_sub(pos))')
sub(f,'usize::try_from(off - pos).unwrap_or(0)','blk.score_offset(off.saturating_sub(pos))')
sub(f,'usize::try_from(at - pos).unwrap_or(0)','blk.score_offset(at.saturating_sub(pos))')
f=r/'mix/src/click.rs';s=f.read_text().replace('pub fn render(s: &Session, pos: Samples, frames: usize, main: &mut [Vec<f32>]) {','''pub(crate) struct Tail {
    frames_rendered: i64,
    hz: f64,
    amp: f32,
}

pub(crate) fn render(s: &Session, block: super::strip::Block, main: &mut [Vec<f32>], tails: &mut Vec<Tail>) {
    let frames = block.frames;
    let pos = block.score.start;''').replace('    let end = pos.saturating_add(frames as i64);','''    tails.retain_mut(|tail| {
        blip(main, -tail.frames_rendered, frames, tail.hz, tail.amp, rate);
        tail.frames_rendered += frames as i64;
        tail.frames_rendered < len
    });
    let end = block.score.end;''')
s=s.replace('    // Start one blip length early so a click that began in an earlier block still rings into this one.\n','').replace('pos.saturating_sub(len)','pos').replace('if at.saturating_add(len) > pos {','if at >= pos {').replace('            blip(main, at - pos, frames, hz, amp as f32, rate);','''            let offset = block.score_offset(at - pos) as i64;
            blip(main, offset, frames, hz, amp as f32, rate);
            let frames_rendered = frames as i64 - offset;
            if frames_rendered < len && tails.len() < tails.capacity() {
                tails.push(Tail { frames_rendered, hz, amp: amp as f32 });
            }''').replace('use soundcraft_time::Samples;','')
f.write_bytes(s.encode())
