from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress/lead-fix/crates/playback/src')
p=d/'midi.rs';s=p.read_text().replace('        let generation = self.clock_render_generation.load(Ordering::SeqCst);\n        let hard = self.clock_render_tick()?;', '''        self.clock_output_window(callback_us,buffer_us,presentation_end_us).0
    }

    pub(crate) fn clock_output_window(&self,callback_us:i64,buffer_us:i64,presentation_end_us:i64)->(Option<i64>,bool) {
        let generation = self.clock_render_generation.load(Ordering::SeqCst);
        let Some(hard) = self.clock_render_tick() else { return (None,false); };''').replace('            return self.clock_render_tick();','            return (self.clock_render_tick(),false);').replace('            return Some(hard);','            return (Some(hard),false);').replace('        Some(hard.saturating_add(extent.saturating_sub(TICKS).max(0)))','        let projected=hard.saturating_add(extent.saturating_sub(TICKS).max(0));\n        (Some(projected),projected>hard)')
p.write_text(s)
p=d/'callback.rs';s=p.read_text();s=s.replace('                let mut projected = false;\n                let through = follow.as_ref().and_then(|feed| {','                let (through,projected) = follow.as_ref().map_or((None,false),|feed| {')
s=s.replace('                        let horizon = feed.clock_render_tick_for_output(feed.clock(), buffer_us, feed.timestamp_at(end));\n                        projected = horizon > feed.clock_render_tick();\n                        return horizon;','                        return feed.clock_output_window(feed.clock(), buffer_us, feed.timestamp_at(end));').replace('                    feed.clock_render_tick()\n                });','                    (feed.clock_render_tick(),false)\n                });');p.write_text(s)

