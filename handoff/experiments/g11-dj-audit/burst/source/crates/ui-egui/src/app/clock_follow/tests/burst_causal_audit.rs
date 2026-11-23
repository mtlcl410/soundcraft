use super::sampler_song::sampler_song;
use super::*;

#[derive(Debug, Clone, Copy)]
enum Delivery {
    Jitter(i64),
    Burst(usize),
    VariableBurst,
    TrailingBurst,
}
fn delivery_times(ideal: &[f64], mode: Delivery) -> Vec<i64> {
    let mut seed = 42u64;
    let mut times = Vec::with_capacity(ideal.len());
    let mut group = 0;
    while times.len() < ideal.len() {
        let p = times.len();
        match mode {
            Delivery::Jitter(amplitude) => {
                seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                let delta = ((seed >> 32) % (2 * amplitude + 1) as u64) as i64 - amplitude;
                times.push(ideal[p].round() as i64 + if p == 0 { 0 } else { delta });
            }
            _ => {
                let n = if let Delivery::Burst(n) = mode { n } else { 3 + group % 3 };
                for j in 0..n.min(ideal.len() - p) {
                    let anchor = if matches!(mode, Delivery::TrailingBurst) {(p+n-1).min(ideal.len()-1)} else {p};
                    times.push(ideal[anchor].round() as i64 + j as i64 * 200);
                }
                group += 1;
            }
        }
    }
    times
}
struct Observation {
    attacks: Vec<Vec<i64>>,
    malformed: usize,
    unmatched: usize,
    steps: Vec<(usize, u8)>,
    dropouts: u64,
}
fn render_train(from: f64, to: f64, transition: usize, n: usize, mode: Delivery, comparator: bool) -> Observation {
    let sr = SampleRate::HZ_48000;
    let inputs = MidiInputs::with_port_names(vec![], vec!["source".into()]);
    let feed = inputs.feed();
    let port = feed.ports().assign("source");
    feed.set_clock_follow(Some(port), true, 0, false);
    feed.set_clock(0);
    feed.receive(port, &[0xfa]);
    let mut now = 0.;
    let ideal: Vec<f64> = (0..n)
        .map(|p| {
            let t = now;
            now += 2_500_000. / if p < transition { from } else { to };
            t
        })
        .collect();
    let times = delivery_times(&ideal, mode);
    let expected: Vec<_> = ideal.iter().step_by(12).map(|at| sr.samples(at / 1e6)).collect();
    let end = sr.samples(now / 1e6) + 48_000;
    let mut song = sampler_song(TempoMap::new(from, 4, 4).unwrap(), sr, expected.len(), end);
    let mut mixer = soundcraft_mix::MixEngine::new(48_000., 512);
    let mut block = vec![vec![0.; 512]; 2];
    let mut pos = 0;
    let mut steps = Vec::new();
    let mut actions = Vec::new();
    let mut dropouts = 0;
    let mut hits: Vec<(i64, Vec<f32>)> = Vec::new();
    let mut sounding = false;
    let mut head: Option<(usize,i64)> = None;
    let mut last_nominal: Option<f64> = None;
    let mut switched = false;
    let mut correction_count = 0;
    let trailing_cmp=comparator && matches!(mode,Delivery::TrailingBurst);
    let mut tail_head_time=None;
    let mut tail_previous:Option<(usize,i64)>=None;
    let mut timer=None;
    for p in 0..=n {
        let until = times.get(p).map_or(end, |at| sr.samples(*at as f64 / 1e6));
        while pos < until {
            if trailing_cmp && let Some(due)=timer && pos>=due {
                timer=None;
                let stamp:i64=tail_head_time.unwrap();
                let index=p-1; // Number of received F8s; never reads the next arrival.
                if let Some((prev_p,prev_stamp))=tail_previous {
                    let measured=(stamp-prev_stamp) as f64 / (index-prev_p) as f64;
                    if let Some(old)=last_nominal {
                        if (old/measured-1.0_f64).abs() >=0.08 {
                            let grid=&mut song.tempo;
                            let edit=grid.samples_to_ticks(pos+1440,sr)+1;
                            let target=(edit/480+1)*480;
                            let es=grid.tick_to_samples(edit,sr);
                            let ts=sr.samples((stamp as f64 + (target as f64/40.-index as f64)*measured)/1e6);
                            if ts>es {
                                grid.set_tempo(edit,(target-edit) as f64*60.*48000./(960.*(ts-es) as f64)).unwrap();
                                grid.set_tempo(target,2_500_000./measured).unwrap();
                                switched=true;
                                correction_count+=1;
                                eprintln!("TAILCORRECTION,{from},{to},{transition},{index},{pos},{es},{ts},{target},{measured:.6}");
                            }
                        }
                    }
                    last_nominal=Some(measured);
                }
                tail_previous=Some((index,stamp));
            }
            let frames = (until.min(timer.unwrap_or(until)) - pos).min(512) as usize;
            mixer.render_with_clock_limit(&song, pos, frames, &mut block, feed.clock_render_tick());
            for (i, &v) in block[0][..frames].iter().enumerate() {
                let high = v.abs() > 0.001;
                if high {
                    if !sounding {
                        hits.push((pos + i as i64, Vec::with_capacity(96)));
                    }
                    hits.last_mut().unwrap().1.push(v);
                }
                sounding = high;
            }
            pos += frames as i64;
        }
        if p < n {
            feed.set_clock(times[p]);
            feed.receive(port, &[0xf8]);
            let snap = feed.clock_follow_status(&mut actions);
            actions.clear();
            if snap.step_intervals != 0 {
                steps.push((p, snap.step_intervals));
            }
            dropouts = snap.dropouts;
            // Causal counterexample scoped to leading-edge group timestamps. Takes only
            // received counts/timestamps, plus the existing 30ms immutable grid guard.
            // No target BPM, transition index, ground truth, or next event is read.
            let group_start = p == 0 || times[p] - times[p-1] > 3000;
            if trailing_cmp && group_start {
                tail_head_time=Some(times[p]);
                timer=Some(sr.samples((times[p]+1001) as f64/1e6));
            }
            if comparator && !trailing_cmp && group_start {
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
            }
        }
    }
    eprintln!("SWITCHES,{from},{to},{transition},{mode:?},{comparator},{correction_count}");
    let baseline = hits.iter().find(|(_,voice)| voice.len()==96).unwrap().1.clone();
    for (i,(at,voice)) in hits.iter().enumerate() {
       let expected_at=expected.get(i).copied().unwrap_or(-99999999);
       eprintln!("HIT,{from},{to},{transition},{mode:?},{comparator},{i},{expected_at},{at},{},{},{}",at-expected_at,voice.len(),voice==&baseline);
    }
    let reference = hits.iter().find(|(_, voice)| voice.len() == 96).unwrap();
    let malformed = hits.iter().filter(|(_, voice)| voice != &reference.1).count() + usize::from(sounding);
    let mut attacks = vec![Vec::new(); expected.len()];
    let mut unmatched = 0;
    for (hit, voice) in hits {
        let right = expected.partition_point(|v| *v < hit);
        let near = match right {
            0 => 0,
            r if r == expected.len() => r - 1,
            r if hit - expected[r - 1] < expected[r] - hit => r - 1,
            r => r,
        };
        let late = hit - expected[near];
        if near + 1 == expected.len() && late > (expected[near] - expected[near - 1]) / 2 {
            unmatched += 1;
        } else {
            attacks[near].push(late);
            eprintln!("ASSIGN,{from},{to},{transition},{mode:?},{comparator},{near},{},{hit},{late},{},{}",expected[near],voice.len(),voice==baseline);
        }
    }
    for (i,slots) in attacks.iter().enumerate() {
        if slots.is_empty() {eprintln!("ASSIGN,{from},{to},{transition},{mode:?},{comparator},{i},{},,,,",expected[i]);}
    }
    Observation { attacks, unmatched, malformed, steps, dropouts }
}
fn record(label: &str, r: &Observation, change: usize) {
    let pre = r.steps.iter().filter(|(p, _)| *p <= change).count();
    let onset = r.steps.iter().find(|(p, _)| *p > change).map(|(p, n)| (p - change, n));
    let missing = r.attacks.iter().filter(|v| v.is_empty()).count();
    let extra = r.attacks.iter().map(|v| v.len().saturating_sub(1)).sum::<usize>() + r.unmatched;
    eprintln!(
        "CASE {label} missing={missing} extra={extra} damaged={} dropouts={} early_steps={pre} confirmations={} first={onset:?}",
        r.malformed,
        r.dropouts,
        r.steps.len()
    );
    if std::env::var_os("SOUNDCRAFT_PACKET_TRACE").is_some() {
        eprintln!("HITS {label} {:?}", r.attacks);
        eprintln!("STEPS {label} {:?}", r.steps);
    }
}

#[test]
#[ignore]
fn grouped_claim_and_causal_counterexample() {
    for (from,to) in [(180.,60.),(130.,80.)] {
        for transition in [384,396] {
            for (mode,cmp) in [(Delivery::VariableBurst,false),(Delivery::VariableBurst,true),(Delivery::TrailingBurst,false),(Delivery::TrailingBurst,true)] {
                let r=render_train(from,to,transition,transition+193,mode,cmp);
                record(&format!("{from}-{to}-{transition}-{mode:?}-{cmp}"), &r,transition);
            }
        }
    }
}
