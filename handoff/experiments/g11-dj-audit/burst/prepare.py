from pathlib import Path
p=Path(__file__).parent
src=p/'source/crates/ui-egui/src/app/clock_follow/tests/packet_steps.rs'
s=src.read_text()
s=s[:s.index('#[test]')]
s=s.replace('VariableBurst,','VariableBurst,\n    TrailingBurst,',1)
s=s.replace('times.push(ideal[p].round() as i64 + j as i64 * 200);','let anchor = if matches!(mode, Delivery::TrailingBurst) {(p+n-1).min(ideal.len()-1)} else {p};\n                    times.push(ideal[anchor].round() as i64 + j as i64 * 200);')
s=s.replace('mode: Delivery) -> Observation','mode: Delivery, comparator: bool) -> Observation')
s=s.replace('    for p in 0..=n {','''    let mut head: Option<(usize,i64)> = None;
    let mut last_nominal: Option<f64> = None;
    let mut switched = false;
    let mut correction_count = 0;
    for p in 0..=n {''',1)
s=s.replace('            update_grid(&mut song.tempo, Some((0, 0)), 0, snap, sr, pos + 1440);','''            // Causal counterexample scoped to leading-edge group timestamps. Takes only
            // received counts/timestamps, plus the existing 30ms immutable grid guard.
            // No target BPM, transition index, ground truth, or next event is read.
            let group_start = p == 0 || times[p] - times[p-1] > 3000;
            if comparator && group_start {
                if let Some((previous, last_stamp)) = head {
                    let measured = (times[p] - last_stamp) as f64 / (p - previous) as f64;
                    if let Some(old) = last_nominal {
                        if (old/measured-1.).abs() >= 0.08 {
                            let grid=&mut song.tempo;
                            let edit=grid.samples_to_ticks(pos+1440,sr)+1;
                            let target=(edit/480+1)*480;
                            let edit_sample = grid.tick_to_samples(edit,sr);
                            let target_sample=sr.samples((times[p] as f64 + (target as f64/40.-p as f64)*measured)/1e6);
                            let delta = target_sample-edit_sample;
                            if delta>0 {
                                let bridge=(target-edit) as f64*60.*48000./(960.*delta as f64);
                                grid.set_tempo(edit,bridge).unwrap();
                                grid.set_tempo(target,2_500_000./measured).unwrap();
                                switched=true;
                                correction_count += 1;
                                eprintln!("CORRECTION,{from},{to},{transition},{mode:?},{p},{},{edit_sample},{target_sample},{target},{measured:.6}",times[p]);
                            }
                        }
                    }
                    last_nominal=Some(measured);
                }
                head=Some((p,times[p]));
            }
            if !switched {
                update_grid(&mut song.tempo, Some((0, 0)), 0, snap, sr, pos + 1440);
            }
            if (transition.saturating_sub(6)..=transition+26).contains(&p) {
                let next_note = (transition+12) as i64*40;
                eprintln!("PULSE,{from},{to},{transition},{mode:?},{comparator},{p},{:.3},{},{},{},{:?},{},{},{},{}",ideal[p],times[p],pos,pos+1440,snap.bpm,snap.step_intervals,snap.packed_delivery,snap.recovering_tempo_step,song.tempo.tick_to_samples(next_note,sr));
            }''')
s=s.replace('    let reference = hits','''    eprintln!("SWITCHES,{from},{to},{transition},{mode:?},{comparator},{correction_count}");
    let baseline = hits.iter().find(|(_,voice)| voice.len()==96).unwrap().1.clone();
    for (i,(at,voice)) in hits.iter().enumerate() {
       let expected_at=expected.get(i).copied().unwrap_or(-99999999);
       eprintln!("HIT,{from},{to},{transition},{mode:?},{comparator},{i},{expected_at},{at},{},{},{}",at-expected_at,voice.len(),voice==&baseline);
    }
    let reference = hits''')
s += '''
#[test]
#[ignore]
fn grouped_claim_and_causal_counterexample() {
    for (from,to) in [(180.,60.),(130.,80.)] {
        for transition in [384,396] {
            for (mode,cmp) in [(Delivery::VariableBurst,false),(Delivery::VariableBurst,true),(Delivery::TrailingBurst,false)] {
                let r=render_train(from,to,transition,transition+193,mode,cmp);
                record(&format!("{from}-{to}-{transition}-{mode:?}-{cmp}"), &r,transition);
            }
        }
    }
}
'''
src.with_name('burst_causal_audit.rs').write_text(s)
parent=src.parent.parent.with_suffix('.rs')
original=parent.read_text()
assert original.count('    mod packet_steps;')==1
parent.write_text(original.replace('    mod packet_steps;','    mod packet_steps;\n    mod burst_causal_audit;'))
