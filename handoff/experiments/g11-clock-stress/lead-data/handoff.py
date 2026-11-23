from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress/lead-fix/crates')
def rep(p,old,new):
 p=d/p;s=p.read_text(); assert old in s,(p,old); p.write_text(s.replace(old,new))
rep('mix/src/lib.rs','''        let frames = frames.min(self.max_block);
        self.begin_block(s, pos, frames);''','''        self.render_clock_block(s,pos,frames,out,through_tick,false);
    }

    /// Schedule the part of this projected block that is still on time at its
    /// actual sample offset, even if earlier wire-limited blocks held a backlog.
    pub fn render_with_clock_prediction(&mut self,s:&Session,pos:Samples,frames:usize,out:&mut [Vec<f32>],through_tick:i64) {
        self.render_clock_block(s,pos,frames,out,Some(through_tick),true);
    }

    fn render_clock_block(&mut self,s:&Session,pos:Samples,frames:usize,out:&mut [Vec<f32>],through_tick:Option<i64>,projected:bool) {
        let frames = frames.min(self.max_block);
        self.begin_block(s, pos, frames);''')
rep('mix/src/lib.rs','let blk = Block { pos, frames, note_start, score, any_solo: any_solo(s) };','let blk = Block { pos, frames, note_start, score, projected, any_solo: any_solo(s) };')
rep('mix/src/strip.rs','    pub(crate) note_start: Samples,','    pub(crate) note_start: Samples,\n    pub(crate) projected: bool,')
rep('mix/src/strip.rs','''        let length = self.score.end.saturating_sub(self.score.start);''','''        if self.projected && self.score.start < self.pos && self.score.end > self.pos {
            // The device can now commit on-time events at their original sample.
            // Only events already overdue are delivered at the start of the block.
            return self.score.start.saturating_add(relative).saturating_sub(self.pos).max(0) as usize;
        }
        let length = self.score.end.saturating_sub(self.score.start);''')
rep('playback/src/callback.rs','fn render_next(&mut self, quantum: usize, through: Option<i64>)','fn render_next(&mut self, quantum: usize, through: Option<i64>, projected: bool)')
rep('playback/src/callback.rs','''        self.mix.render_with_clock_limit(&self.session, self.pos, n, &mut self.pending, through);''','''        if let Some(limit) = through.filter(|_| projected) {
            self.mix.render_with_clock_prediction(&self.session,self.pos,n,&mut self.pending,limit);
        } else {
            self.mix.render_with_clock_limit(&self.session, self.pos, n, &mut self.pending, through);
        }''')
rep('playback/src/callback.rs','''                let through = follow.as_ref().and_then(|feed| {''','''                let mut projected = false;
                let through = follow.as_ref().and_then(|feed| {''')
rep('playback/src/callback.rs','''                        return feed.clock_render_tick_for_output(feed.clock(), buffer_us, feed.timestamp_at(end));''','''                        let horizon = feed.clock_render_tick_for_output(feed.clock(), buffer_us, feed.timestamp_at(end));
                        projected = horizon > feed.clock_render_tick();
                        return horizon;''')
rep('playback/src/callback.rs','''                self.render_next(render_frames, through);''','''                self.render_next(if projected { render_frames } else { quantum }, through, projected);''')

