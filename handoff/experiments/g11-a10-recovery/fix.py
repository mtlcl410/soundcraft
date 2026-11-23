from pathlib import Path
d=Path(__file__).resolve().parent
def sub(path,a,b):
 s=path.read_text()
 assert a in s,(path,a)
 path.write_bytes(s.replace(a,b).encode())
for n in ('beat','mtc','follow'):
 p=d/n/'crates/playback/src'
 f=p/'sync_clock.rs'
 sub(f,'    blocks: VecDeque<Presentation>,','''    blocks: VecDeque<Presentation>,
    // Only the consecutive timed blocks after the latest loss can drive compensated output.
    timed_blocks: usize,
    pub(crate) timing_epoch: u64,''')
 sub(f,'            blocks: VecDeque::with_capacity(HISTORY),','''            blocks: VecDeque::with_capacity(HISTORY),
            timed_blocks: 0,
            timing_epoch: 0,''')
 sub(f,'        if block.lead.is_some()\n', '''        if block.lead.is_some() {
            self.timed_blocks = (self.timed_blocks + 1).min(HISTORY);
        } else if self.timed_blocks > 0 {
            self.timed_blocks = 0;
            self.timing_epoch = self.timing_epoch.wrapping_add(1);
        }
        if block.lead.is_some()
''')
 sub(f,'        if compensate && self.blocks.back().is_none_or(|b| b.lead.is_none()) {\n            return (None, None);\n        }','''        let first = if compensate { self.blocks.len() - self.timed_blocks } else { 0 };''')
 sub(f,'self.blocks.iter().enumerate().rev().find_map','self.blocks.range(first..).enumerate().rev().find_map')
 sub(f,'self.blocks.iter().find_map(adjusted)','self.blocks.range(first..).find_map(adjusted)')
 sub(f,'.range(index + 1..)','.range(first + index + 1..)')
 sub(f,'    fn reset(&mut self);','''    fn reset(&mut self);
    /// Previously queued deadlines on a compensated route are no longer usable.
    fn timing_lost(&mut self) {
        self.reset();
    }''')
 f=p/'sync_output.rs'
 sub(f,'    waiting_for_timing: bool,','    timing_epochs: [u64; 2],\n    waiting_for_timing: bool,')
 sub(f,'        waiting_for_timing: false,','        timing_epochs: [0; 2],\n        waiting_for_timing: false,')
 for a in ('block, future, revision','block, future, changed'):
  sub(f,'('+a,'(timing_epoch, '+a) if a.endswith('revision') else sub(f,'('+a,'(timeline.timing_epoch, '+a)
 sub(f,'            if let Some(new) = revision {','''            if r.compensate && self.timing_epochs[route_index] != timing_epoch {
                self.timing_epochs[route_index] = timing_epoch;
                self.future.retain(|event| event.route != route_index);
                pending.retain(|event| event.route != route_index);
                r.encoder.timing_lost();
            }
            if let Some(new) = revision {''')
 f=p/'sync_output_tests.rs'
 sub(f,'        waiting_for_timing: false,','        timing_epochs: [0; 2],\n        waiting_for_timing: false,')
 sub(p/'beat_clock.rs','impl SyncEncoder for Cursor {','''impl SyncEncoder for Cursor {
    fn timing_lost(&mut self) {
        // A receiver missed pulses. Reposition it using SPP before sending fresh clocks.
        self.remap |= self.last_position.is_some();
    }''')
 if n!='beat':
  f=p/'mtc.rs'
  sub(f,'    pass: Option<(u64, bool)>,','    pass: Option<(u64, bool)>,\n    lost_while_rolling: bool,')
  sub(f,'        if relaunch {','        let recovering = std::mem::take(&mut self.lost_while_rolling);\n        if relaunch || recovering {')
  sub(f,'let recent_origin = block.playing','let recent_origin = !recovering && block.playing')
  sub(f,'    fn reset(&mut self) {\n        self.pass = None;','''    fn timing_lost(&mut self) {
        self.lost_while_rolling |= self.pass.is_some_and(|(_, playing)| playing);
    }
    fn reset(&mut self) {
        self.lost_while_rolling = false;
        self.pass = None;''')
