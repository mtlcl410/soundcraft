
#[test]
fn classify() {
    let mut wrong=0;
    for amplitude in [0,1000] {for pct in [-8.1_f64,-8.,-7.9,7.9,8.,8.1] {
        let mut trials=Vec::new();
        for trial in 0..10 {
            if std::env::var_os("EDGE_DEBUG").is_some() && (amplitude!=0 || pct!=8. || trial>0) {continue;}
            let cut=384+trial; let mut t=0.0_f64; let mut seed=42+trial as u64;
            let mut f=Follower::default(); f.coast=true; f.receive(&[0xfa],0);
            let mut events=Vec::new();
            for p in 0..=cut+192 {
                seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                let at=t.round() as i64 + if p==0 {0}else{((seed>>32)%((amplitude*2+1) as u64)) as i64-amplitude};
                f.receive(&[0xf8],at); if f.step_intervals>0 {events.push(p as i64-cut as i64);}
                t+=2_500_000. / if p<cut {128.}else{128.*(1.+pct/100.)};
            }
            if (pct.abs()<8. && !events.is_empty()) || (pct.abs()>=8. && (events.len()!=1 || events[0]<1)) {wrong+=1;}
            trials.push(events);
        }
        eprintln!("CLASS {pct} jitter{amplitude}: {trials:?}");
    }}
    assert_eq!(wrong,0);
}

fn gaussian(seed: &mut u64) -> f64 {
    let mut unit = || {
        *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        ((*seed >> 11) as f64 + 1.) / ((1u64 << 53) as f64 + 1.)
    };
    (-2. * unit().ln()).sqrt() * (std::f64::consts::TAU * unit()).cos()
}

#[test]
fn locks_and_predicts_pulses_across_tempos_jitter_and_usb_quantization() {
    for bpm in [90., 120., 174.] {
        for jitter in [500., 2000., 4000.] {
            let mut r = Follower::default();
            let mut seed = 100;
            let mut errors = Vec::new();
            let mut phase_errors = Vec::new();
            let interval = 60_000_000. / (24. * bpm);
            for pulse in 0..700 {
                let ideal = 100_000. + pulse as f64 * interval;
                let us = ((ideal + gaussian(&mut seed) * jitter) / 1000.).round() as i64 * 1000;
                r.receive(&[0xf8], us);
                if pulse == 23 {
                    assert!((r.bpm().unwrap() - bpm).abs() < 2., "failed to acquire within a beat");
                }
                if pulse >= 24 {
                    assert!(!r.steady.is_tempo_ramp(), "false ramp at {bpm} BPM/{jitter} us, pulse {pulse}");
                }
                if pulse >= 240 {
                    errors.push((r.bpm().unwrap() - bpm).abs());
                    phase_errors.push((r.phase_error_us as f64).abs());
                }
            }
            errors.sort_by(f64::total_cmp);
            phase_errors.sort_by(f64::total_cmp);
            let p95 = errors[errors.len() * 95 / 100];
            eprintln!("steady {bpm} {jitter} BPMp95={p95:.8} phasep95_us={:.4}", phase_errors[phase_errors.len() * 95 / 100]);
            if bpm == 120. && jitter == 2000. {
                assert!(errors.iter().all(|err| *err < 0.05), "steady-state BPM crossed the display tolerance");
            }
            assert!(p95 < if bpm == 120. && jitter <= 2000. { 0.05 } else { 0.25 }, "{bpm} BPM/{jitter} us: {p95}");
            assert!(phase_errors[phase_errors.len() * 95 / 100] <= jitter * 3.5 + 1000.);
        }
    }
}



#[test]
fn nudge_and_staircase_classification() {
 for jitter in [0,1000] {
  for (pct,duration) in [-5.,-3.5,-2.,2.,3.5,5.].into_iter().flat_map(|pct|[500_000.,1_000_000.,2_000_000.].into_iter().map(move |duration| (pct,duration))).chain([(0.,0.)]) {
   let mut levels=vec![120.0_f64]; while *levels.last().unwrap()<132. {levels.push((*levels.last().unwrap()*1.01).min(132.));} while *levels.last().unwrap()>120. {levels.push((*levels.last().unwrap()*0.99).max(120.));}
   let mut f=Follower::default(); f.coast=true;f.receive(&[0xfa],0);
   let mut t=0.0_f64;let mut rng=42u64;let mut ev=vec![];
   for p in 0..=1032 {
    rng=rng.wrapping_mul(6364136223846793005).wrapping_add(1);let delta=if p==0{0}else{((rng>>32)%((2*jitter+1) as u64)) as i64-jitter};
    let at=t.round() as i64+delta;f.receive(&[0xf8],at);if f.step_intervals>0 {ev.push((p,f.step_intervals));}
    let end=384.*2_500_000./128.+duration;
    t+=if pct==0. {2_500_000./levels[if p<384{0}else{((p-384)/24+1).min(levels.len()-1)}]}else if p<384||t>=end{2_500_000./128.}else{let period=2_500_000./(128.*(1.+pct/100.));let left=end-t;if left>=period {period}else{left+(2_500_000./128.)*(1.-left/period)}};
   }
   eprintln!("OTHER {pct} {duration} {jitter}: {ev:?}");assert!(ev.is_empty());
  }
 }
}
