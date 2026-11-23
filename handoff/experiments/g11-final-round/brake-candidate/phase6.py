from pathlib import Path
c=Path('../brake-candidate')
p=c/'crates/playback/src/clock_follow.rs';s=p.read_text().replace('fn phase_tracking(&self) -> bool { self.tracking_pulses','fn phase_tracking(&self) -> bool { self.state==State::Locked && self.tracking_pulses')
s=s.replace('0 if self.phase_tracking() => at,','0 if self.phase_tracking() => at,').replace('self.step_pulses_left = 24;', 'self.tracking_pulses=0;self.step_pulses_left = 24;')
p.write_text(s)
p=c/'crates/ui-egui/src/app/clock_follow.rs';s=p.read_text();s=s.replace('    // A batched acceleration can report','''    if s.phase_grid_bpm.is_some() && s.state==State::Locked && s.pulse>origin {
        let edit=tick+1;
        let edi=grid.tick_to_samples(edit,sr);
        let wire_sample=grid.tick_to_samples(origin*TICKS_PER_PULSE,sr)+sr.samples((s.stamp_us-stamp) as f64/1e6);
        let spp=sr.hz() as f64 * 60. / (bpm * TICKS_PER_QUARTER as f64);
        let drift=(edit-tick) as f64*spp + (wire_sample-edi) as f64;
        let period=spp*(1. + (drift/(TICKS_PER_PULSE as f64*spp)).clamp(-0.4,0.4));
        let effective=60.*sr.hz() as f64/(period*TICKS_PER_QUARTER as f64);
        if (grid.tempo_at_tick(edit)-effective).abs()>0.03 {
            while let Some(t)=grid.tempos().last().map(|e|e.tick).filter(|t|*t>edit) { grid.remove_tempo(t); }
            return grid.set_tempo(edit,effective).is_ok();
        }
        return false;
    }
    // A batched acceleration can report''');p.write_text(s)
