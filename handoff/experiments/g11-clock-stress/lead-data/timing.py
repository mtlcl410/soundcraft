from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress/lead-fix/crates/playback/src');p=d/'midi.rs';s=p.read_text();mark='    /// Microseconds since the feed was made.';s=s.replace(mark,'''    /// Convert a device presentation timestamp (on the host monotonic clock) to
    /// the epoch used by incoming driver timestamps.
    #[cfg(any(target_os = "linux", target_os = "macos", target_os = "windows"))]
    pub(crate) fn timestamp_at(&self, instant: Instant) -> i64 {
        i64::try_from(instant.saturating_duration_since(self.epoch).as_micros()).unwrap_or(i64::MAX)
    }

'''+mark);p.write_text(s)
p=d/'callback.rs';s=p.read_text();s=s.replace('        #[cfg(any(target_os = "linux", target_os = "macos", target_os = "windows"))]\n        let callback_us = follow.as_ref().map_or(0, |feed| feed.clock());\n','');i=s.index('                let through = follow.as_ref()');j=s.index('                #[cfg(any(target_os',s.index('                self.render_next(quantum, through);',i));s=s[:i]+'''                let remaining = callback_frames - frame_index;
                // Do not commit a full internal quantum past the physical callback end.
                let render_frames = if follow.is_some() {
                    quantum.min((remaining as f64 * step + self.read).ceil() as usize).max(1)
                } else { quantum };
                let through = follow.as_ref().and_then(|feed| {
                    #[cfg(any(target_os = "linux", target_os = "macos", target_os = "windows"))]
                    if let Some(timing) = self.device_timing.filter(|t| !t.clamped && t.lead().is_some()) {
                        // The device stamp belongs to the original callback, including when
                        // stream.rs splits it into chunks. Adding lead to the current wall
                        // time instead would double-count rendering time in later chunks.
                        let device_frames = ((render_frames as f64 - self.read) / step).ceil() as usize;
                        let end = timing.heard_instant(self.device_rate, frame_index + device_frames.min(remaining));
                        let buffer_us = (self.device_buffer_frames as f64 * 1e6 / self.device_rate).round() as i64;
                        return feed.clock_render_tick_for_output(feed.clock(), buffer_us, feed.timestamp_at(end));
                    }
                    feed.clock_render_tick()
                });
                self.render_next(render_frames, through);
'''+s[j:];p.write_text(s)
p=d/'clock_follow/render_lead.rs';s=p.read_text().replace('    let start = Instant::now();','    let start = Instant::now();\n    let epoch = feed.timestamp_at(start);').replace('    feed.set_clock(0);\n    feed.receive(1, &[0xfa]);\n    let mut out','    feed.set_clock(epoch);\n    feed.receive(1, &[0xfa]);\n    let mut out').replace('feed.set_clock((pulse * 60_000_000','feed.set_clock(epoch + (pulse * 60_000_000').replace('feed.set_clock((at * 1_000_000','feed.set_clock(epoch + (at * 1_000_000');p.write_text(s)

