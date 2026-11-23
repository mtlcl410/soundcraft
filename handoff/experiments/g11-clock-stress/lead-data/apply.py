from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress/lead-fix/crates/playback/src')
def sub(path,a,b):
 p=d/path;s=p.read_text('utf8');assert a in s,(path,a);p.write_text(s.replace(a,b),'utf8')
sub('sync_input.rs','    pub fn period_us(&self)', '''    /// Prediction requires several independently observed intervals at the fitted rate.
    pub(crate) fn regular_intervals(&self, period: f64) -> bool {
        const COUNT: usize = 4;
        if self.len <= COUNT {
            return false;
        }
        let start = (self.cursor + N - COUNT - 1) % N;
        (0..COUNT).all(|i| {
            let elapsed = self.points[(start+i+1)%N].1.saturating_sub(self.points[(start+i)%N].1);
            (elapsed as f64 - period).abs() <= (0.02 * period).max(2.)
        })
    }

    pub fn period_us(&self)''')
sub('clock_follow.rs','    fn bpm(&self)', '''    pub(crate) fn render_prediction(&self) -> Option<(i64,f64)> {
        let period = self.steady.period_us()?;
        if self.state != State::Locked || self.step_pulses_left != 0 || !(2500. ..=500_000.).contains(&period) || !self.short.regular_intervals(period) {
            return None;
        }
        Some((self.latest?,period))
    }

    fn bpm(&self)''')
sub('midi.rs','    clock_render_pulse: AtomicI64,','''    // A single writer (under clock_follow) publishes an optional period and its matching pulse.
    // The callback never waits for a writer; a concurrent change disables prediction for that read.
    clock_render_generation: AtomicU64,
    clock_render_pulse: AtomicI64,
    clock_render_stamp: AtomicI64,
    clock_render_period: AtomicU64,''')
sub('midi.rs','            clock_render_pulse: AtomicI64::new(i64::MAX),','''            clock_render_generation: AtomicU64::new(0),
            clock_render_pulse: AtomicI64::new(i64::MAX),
            clock_render_stamp: AtomicI64::new(0),
            clock_render_period: AtomicU64::new(0),''')
sub('midi.rs','self.clock_render_pulse.store(i64::MAX, Ordering::Release);','self.publish_clock_render(&input);')
sub('midi.rs','self.clock_render_pulse.store(input.render_through_pulse().unwrap_or(i64::MAX), Ordering::Release);','self.publish_clock_render(&input);')
sub('midi.rs','    /// Inclusive clip/click event horizon.', '''    fn publish_clock_render(&self, input: &crate::clock_follow::Follower) {
        let pulse = input.render_through_pulse().unwrap_or(i64::MAX);
        let (stamp, period) = input.render_prediction().unwrap_or((0,0.));
        self.clock_render_generation.fetch_add(1, Ordering::SeqCst);
        self.clock_render_pulse.store(pulse, Ordering::SeqCst);
        self.clock_render_stamp.store(stamp, Ordering::SeqCst);
        self.clock_render_period.store(period.to_bits(), Ordering::SeqCst);
        self.clock_render_generation.fetch_add(1, Ordering::SeqCst);
    }

    /// Latest tick that can be scheduled for this immutable device block. Times are
    /// microseconds in the input feed's epoch. A short buffer, uncertain lock, stale
    /// pulse or concurrent source change keeps the ordinary one-pulse wire limit.
    pub fn clock_render_tick_for_output(&self, callback_us: i64, buffer_us: i64, presentation_end_us: i64) -> Option<i64> {
        let generation = self.clock_render_generation.load(Ordering::SeqCst);
        let hard = self.clock_render_tick()?;
        let stamp = self.clock_render_stamp.load(Ordering::SeqCst);
        let period = f64::from_bits(self.clock_render_period.load(Ordering::SeqCst));
        if generation % 2 != 0 || self.clock_render_generation.load(Ordering::SeqCst) != generation {
            return self.clock_render_tick();
        }
        let age = callback_us.saturating_sub(stamp);
        if period == 0. || (buffer_us as f64) < period || age < 0 || age > period.ceil() as i64 || presentation_end_us <= callback_us {
            return Some(hard);
        }
        const TICKS: i64 = soundcraft_time::TICKS_PER_QUARTER / 24;
        let elapsed = presentation_end_us.saturating_sub(stamp) as f64;
        let extent = (elapsed * TICKS as f64 / period).ceil() as i64;
        Some(hard.saturating_add(extent.saturating_sub(TICKS).max(0)))
    }

    /// Inclusive clip/click event horizon.''')
sub('callback.rs','fn render_next(&mut self, quantum: usize)','fn render_next(&mut self, quantum: usize, through: Option<i64>)')
sub('callback.rs','        let through = if self.playing && self.following_clock { self.midi.as_ref().and_then(|feed| feed.clock_render_tick()) } else { None };\n','')
sub('callback.rs','        for (frame_index, frame) in out.chunks_mut(channels).enumerate() {','''        let follow = if self.playing && self.following_clock { self.midi.clone() } else { None };
        #[cfg(any(target_os = "linux", target_os = "macos", target_os = "windows"))]
        let callback_us = follow.as_ref().map_or(0, |feed| feed.clock());
        for (frame_index, frame) in out.chunks_mut(channels).enumerate() {''')
sub('callback.rs','                self.render_next(quantum);','''                let through = follow.as_ref().and_then(|feed| {
                    #[cfg(any(target_os = "linux", target_os = "macos", target_os = "windows"))]
                    if let Some(timing) = self.device_timing.filter(|t| !t.clamped)
                        && let Some(lead) = timing.lead()
                    {
                        // Device streams can be split into scratch chunks and each chunk into
                        // mix quanta. Predict only through samples committed by this render.
                        let frame_us = 1e6 / self.device_rate;
                        let frames = (timing.frame_offset + frame_index) as f64 + quantum as f64 / step;
                        let duration = (frames * frame_us).ceil() as i64;
                        let end = callback_us.saturating_add(lead.as_micros() as i64).saturating_add(duration);
                        return feed.clock_render_tick_for_output(callback_us,(self.device_buffer_frames as f64 * frame_us).round() as i64,end);
                    }
                    feed.clock_render_tick()
                });
                self.render_next(quantum,through);''')

