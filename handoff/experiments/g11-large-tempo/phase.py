from pathlib import Path
r=Path('work/crates')
f=r/'playback/src/sync_input.rs';s=f.read_text()
a=s.index('        const INTERVALS: usize = 4;');b=s.index('        Some(start)',a)
s=s[:a]+'''        // Two nearly identical intervals can distinguish a large jump from a
        // delayed packet followed by a short one. Keep the four-interval noise
        // test for ordinary changes and for devices with appreciable jitter.
        self.step_intervals(previous, noise_us, 2, 0.30, 0.03)
            .or_else(|| self.step_intervals(previous, noise_us, 4, 0.08, 0.4))
    }

    fn step_intervals(&self, previous: f64, noise_us: f64, count: usize, threshold: f64, tolerance: f64) -> Option<(i64, i64)> {
'''+s[a:b].split('\n',1)[1].replace('INTERVALS','count').replace('(previous * 0.08).max(2. * noise_us)','(previous * threshold).max(if count == 2 { 8. } else { 2. } * noise_us)').replace('change.abs() * 0.4','change.abs() * tolerance')+s[b:];f.write_bytes(s.encode())
f=r/'ui-egui/src/app/clock_follow.rs';s=f.read_text()
a=s.index('    // During a confirmed step');b=s.index('\n}',a)
s=s[:a]+'''    if s.recovering_tempo_step {
        // Join the new wire grid at a future pulse. Only the interval after
        // the committed audio changes; then restore the source's exact tempo.
        let edit_sample = grid.tick_to_samples(edit, sr);
        let elapsed_at_edit = sr.seconds(edit_sample - start - elapsed);
        let wire_at_edit = tick as f64 + elapsed_at_edit * bpm * TICKS_PER_QUARTER as f64 / 60.;
        let ahead = (edit as f64).max(wire_at_edit);
        let join = ((ahead / TICKS_PER_PULSE as f64).ceil() as i64 + 1) * TICKS_PER_PULSE;
        let seconds = (join as f64 - wire_at_edit) * 60. / (bpm * TICKS_PER_QUARTER as f64);
        let bridge = (join - edit) as f64 * 60. / (seconds * TICKS_PER_QUARTER as f64);
        if grid.set_tempo(edit, bridge.clamp(5., 1000.)).is_ok() {
            let _ = grid.set_tempo(join, bpm);
            return true;
        }
        return false;
    }
    let recovery_beats = if phase.abs() <= 0.006 { 8. } else { 4. };
    let target = bpm / (1. + (phase * bpm / (60. * recovery_beats)).clamp(-0.05, 0.05));
    (slope - target).abs() >= 0.15 && grid.set_tempo(edit, target.clamp(5., 1000.)).is_ok()
'''+s[b:];a=s.rindex('    #[test]',0,s.index('    fn chorus_tempo_step_keeps_'));b=s.index('    #[test]',a+10);s=s[:a]+s[b:];f.write_bytes(s.encode())
