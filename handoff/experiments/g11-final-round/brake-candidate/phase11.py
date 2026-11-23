from pathlib import Path
p=Path('../brake-candidate/crates/ui-egui/src/app/clock_follow.rs');s=p.read_text().replace('((ahead / TICKS_PER_PULSE as f64).ceil() as i64).saturating_add(1)', '((ahead / TICKS_PER_PULSE as f64 + if s.phase_grid_bpm.is_some() {0.30} else {1.0}).ceil() as i64)');p.write_text(s)
