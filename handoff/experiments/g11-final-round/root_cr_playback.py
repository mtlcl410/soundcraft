from pathlib import Path
def rep(path,a,b):
 p=Path(path);s=p.read_text('utf8');assert s.count(a)==1,(path,a);p.write_text(s.replace(a,b),'utf8')
c='crates/playback/src/callback.rs'
rep(c,'    pending: Vec<Vec<f32>>,','    pending: Vec<Vec<f32>>,\n    pending_rate: f64,')
rep(c,'            pending_len: 0,','            pending_rate: device_rate,\n            pending_len: 0,')
rep(c,'        self.pending_len = n;','        self.pending_len = n;\n        self.pending_rate = self.session.sample_rate.as_f64();')
rep(c,'            let sample = self.pos as f64 - self.pending_len as f64 + self.read;', '            let sample = if self.playing { self.pos as f64 - self.pending_len as f64 + self.read } else { self.pos as f64 };')
rep(c,'            block.sample_rate = sample_rate;', '''            block.sample_rate = sample_rate;
            block.samples_per_second = speed * sample_rate.as_f64();
            block.limit = block.sample + callback_frames as f64 * block.samples_per_second / self.device_rate.max(1.);''')
rep(c,'        for (frame_index, frame) in out.chunks_mut(channels).enumerate() {','''        let mut read_step = if self.pending_len == 0 { step } else { speed * self.pending_rate / self.device_rate.max(1.) };
        for (frame_index, frame) in out.chunks_mut(channels).enumerate() {''')
rep(c,'                self.render_next(quantum);','''                // The unconsumed fraction is in the outgoing revision's units.
                if read_step != step {
                    self.read *= step / read_step;
                    read_step = step;
                }
                self.render_next(quantum);''')
rep(c,'            self.read += step;', '            self.read += read_step;')
rep(c,'tail.limit = tail.sample + at as f64 * step;', 'tail.limit = tail.sample + at as f64 * tail.samples_per_second / self.device_rate.max(1.);')
rep(c,'                        continue;\n                    }\n                    self.recording = r;', '''                        if let Some(feed) = &self.midi {
                            feed.finish_pending_start(false);
                        }
                        continue;
                    }
                    self.recording = r;''')
rep(c,'feed.pass_begun();','feed.finish_pending_start(true);')
m='crates/playback/src/midi.rs'
rep(m,'''        let n = self.events.len();
        let r = self.read.load(Ordering::Relaxed);
        if r == self.write.load(Ordering::Acquire) {''','''        self.pop_until(self.write.load(Ordering::Acquire))
    }

    fn pop_until(&self, end: usize) -> Option<(i64, u32)> {
        let n = self.events.len();
        let r = self.read.load(Ordering::Relaxed);
        if r == end {''')
rep(m,'    recorded: Ring,','''    recorded: Ring,
    /// Only accepted takes are visible to the UI. The audio writer may stage a punch-in
    /// in this same ring while its start command is pending.
    recorded_visible: AtomicUsize,
    pending_lost: AtomicU32,
    pending_gap: AtomicBool,''')
rep(m,'            recorded: Ring::new(RECORDED),','''            recorded: Ring::new(RECORDED),
            recorded_visible: AtomicUsize::new(0),
            pending_lost: AtomicU32::new(0),
            pending_gap: AtomicBool::new(false),''')
rep(m,'''        if self.record_gap.load(Ordering::Relaxed) {
            if !self.recorded.push(at, lost_entry(u8::MAX)) {
                self.recorded_lost.fetch_add(1, Ordering::Relaxed);
                return;
            }
            self.record_gap.store(false, Ordering::Relaxed);
        }
        if !self.recorded.push(at, entry) {
            self.recorded_lost.fetch_add(1, Ordering::Relaxed);
            self.record_gap.store(true, Ordering::Relaxed);
        }''','''        let pending = self.begin_pending();
        let (gap, losses) = if pending { (&self.pending_gap, &self.pending_lost) } else { (&self.record_gap, &self.recorded_lost) };
        if gap.load(Ordering::Relaxed) {
            if !self.recorded.push(at, lost_entry(u8::MAX)) {
                losses.fetch_add(1, Ordering::Relaxed);
                return;
            }
            gap.store(false, Ordering::Relaxed);
        }
        if !self.recorded.push(at, entry) {
            losses.fetch_add(1, Ordering::Relaxed);
            gap.store(true, Ordering::Relaxed);
        }
        if !pending {
            self.recorded_visible.store(self.recorded.write.load(Ordering::Relaxed), Ordering::Release);
        }''')
rep(m,'''    pub(crate) fn pass_begun(&self) {
        self.begin_pending.store(false, Ordering::Release);''','''    pub(crate) fn finish_pending_start(&self, accepted: bool) {
        if !self.begin_pending.swap(false, Ordering::AcqRel) {
            return;
        }
        let losses = self.pending_lost.swap(0, Ordering::Relaxed);
        let gap = self.pending_gap.swap(false, Ordering::Relaxed);
        if accepted {
            self.recorded_lost.fetch_add(losses, Ordering::Relaxed);
            if gap { self.record_gap.store(true, Ordering::Relaxed); }
            self.recorded_visible.store(self.recorded.write.load(Ordering::Relaxed), Ordering::Release);
        } else {
            // No consumer has seen the tentative suffix. Rewind only the producer cursor.
            self.recorded.write.store(self.recorded_visible.load(Ordering::Relaxed), Ordering::Relaxed);
        }''')
rep(m,'        while let Some((at, e)) = self.recorded.pop() {','        let end = self.recorded_visible.load(Ordering::Acquire);\n        while let Some((at, e)) = self.recorded.pop_until(end) {')

