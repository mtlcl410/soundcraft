from pathlib import Path
c=Path('../brake-candidate')
p=c/'crates/playback/src/clock_follow.rs';s=p.read_text().replace('fn phase_tracking(&self) -> bool { self.tracking_pulses','fn phase_tracking(&self) -> bool { self.state==State::Locked && self.tracking_pulses')
s=s.replace('self.step_pulses_left = 24;', 'self.tracking_pulses=0;self.step_pulses_left = 24;')
p.write_text(s)
p=c/'crates/ui-egui/src/app/clock_follow.rs';s=p.read_text()
o=s.index('    // A batched acceleration can report');e=s.index('    let before = grid.tempos()',o)
s=s[:o]+'''    let start = grid.tick_to_samples(origin.saturating_mul(TICKS_PER_PULSE), sr);
    let elapsed = sr.samples(s.stamp_us.saturating_sub(stamp) as f64 / 1e6);
    let phase = sr.seconds(start.saturating_add(elapsed).saturating_sub(grid.tick_to_samples(tick, sr)));
    let precise= !s.packed_delivery && !s.braking && s.jitter_us<1400. && phase.abs()>0.0012;
    let correcting=s.recovering_tempo_step || precise;
    let edit=if render_until>0 && (precise || s.phase_grid_bpm.is_some() || (s.packed_delivery || s.braking) && s.recovering_tempo_step) { writable.max(origin.saturating_mul(TICKS_PER_PULSE)) }else{tick.max(writable)};
    let check_tick=if correcting {edit}else{tick};
    if grid.tempos().last().is_some_and(|e|e.tick>check_tick) {
        if s.phase_grid_bpm.is_some() || precise {
            while let Some(t)=grid.tempos().last().map(|e|e.tick).filter(|t|*t>edit) {grid.remove_tempo(t);}
        }else{return false;}
    }
'''+s[e:]
a=s.index('    let spacing = if');b=s.index('        // Join the new wire grid',a)
sub=s[a:b].replace('let spacing = if s.recovering_tempo_step', 'let spacing = if precise || s.phase_grid_bpm.is_some() {0} else if s.recovering_tempo_step')
i=sub.index('    let start =');j=sub.index('    let (bpm_deadband',i);sub=sub[:i]+sub[j:]
sub=sub.replace('if s.recovering_tempo_step &&','if correcting &&').replace('if s.recovering_tempo_step {','if correcting {').replace('&& phase.abs() < phase_deadband {','&& phase.abs() < phase_deadband && !precise {')
s=s[:a]+sub+s[b:];p.write_text(s)
