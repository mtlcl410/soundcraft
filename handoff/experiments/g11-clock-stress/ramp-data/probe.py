from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress')
r=d/'ramps/crates/ui-egui/src/app/clock_follow';p=r/'tests/ramp_response.rs';s=p.read_text()
(d/'ramp-data/ramp-test.rs').write_text(s)
a=r.with_suffix('.rs').read_text();a=a[a.index('fn update_grid(grid:'):a.index('#[cfg(test)]\nmod tests')]
a=a.replace('fn update_grid(grid:', 'fn candidate_grid(ramp:bool, grid:').replace('let spacing = if s.recovering_tempo_step { 2 }', 'let spacing = if s.recovering_tempo_step || ramp { 2 }').replace('if (slope - bpm).abs() < 0.15 && phase.abs() < 0.003','if (slope - bpm).abs() < if ramp {0.035} else {0.15} && phase.abs() < if ramp {0.0005} else {0.003}').replace('if phase.abs() <= 0.006 { 8. }','if ramp {0.6} else if phase.abs() <= 0.006 { 8. }').replace('(slope - target).abs() >= 0.15','(slope - target).abs() >= if ramp {0.035} else {0.15}')
s=s.replace('let mut signed=Vec::new();','let mut signed=Vec::new(); let mut history=Vec::new();let mode=std::env::var("RAMP_PROBE").unwrap_or_default();let mut adaptive=0;')
s=s.replace('                update_grid(&mut song.tempo,Some((0,20000)),0,snap,sr,sr.samples(at as f64/1e6+0.030));','''                history.push(at as f64);
                let n=(history.len()/3).min(64);
                let mut corrected=snap;
                let mut ramp=false;
                if n>=8 && !snap.recovering_tempo_step {
                    let mean=|slice:&[f64]|slice.iter().sum::<f64>()/n as f64;
                    let start=history.len()-3*n;
                    let l=mean(&history[start..start+n]);
                    let m=mean(&history[start+n..start+2*n]);
                    let r=mean(&history[start+2*n..]);
                    let width=n as f64;
                    let curvature=(r-m)-(m-l);
                    let sigma=snap.jitter_us*(6./width).sqrt();
                    let period=(r-l)/(2.*width);
                    let accel=curvature/(width*width);
                    ramp=curvature.abs()> (2.0*sigma).max(period*period*width*width*0.00045/1e6);
                    let x=(3.*width-1.)/2.;
                    if mode=="quadratic" && ramp {
                        corrected.bpm=Some(2_500_000./(period+accel*x));
                        corrected.stamp_us=20000+(m + period*x+0.5*accel*(x*x-(width*width-1.)/12.)).round() as i64;
                    }
                }
                if mode=="always" {ramp=true;}
                if mode=="baseline" {ramp=false;}
                adaptive+=usize::from(ramp);
                candidate_grid(ramp,&mut song.tempo,Some((0,20000)),0,corrected,sr,sr.samples(at as f64/1e6+0.030));''')
s=s.replace('locked_jump={jump:.5}', 'adaptive={adaptive} locked_jump={jump:.5}')
p.write_text(s+'\n'+a)

