from pathlib import Path
d=Path(__file__).parent
f=d/'source/crates/ui-egui/src/app/clock_follow/tests/burst_causal_audit.rs';s=f.read_text(encoding='utf-8')
s=s.replace('    for p in 0..=n {','''    let trailing_cmp=comparator && matches!(mode,Delivery::TrailingBurst);
    let mut tail_head_time=None;
    let mut tail_previous=None;
    let mut timer=None;
    for p in 0..=n {''')
s=s.replace('            let frames = (until - pos).min(512) as usize;', '''            if trailing_cmp && let Some(due)=timer && pos>=due {
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
            let frames = (until.min(timer.unwrap_or(until)) - pos).min(512) as usize;''')
s=s.replace('            if comparator && group_start {','''            if trailing_cmp && group_start {
                tail_head_time=Some(times[p]);
                timer=Some(sr.samples((times[p]+1001) as f64/1e6));
            }
            if comparator && !trailing_cmp && group_start {''')
s=s.replace('let mut last_nominal: Option<f64> = None;','let mut last_nominal: Option<f64> = None;')
s=s.replace('let mut tail_previous=None;','let mut tail_previous:Option<(usize,i64)>=None;')
s=s.replace('(Delivery::TrailingBurst,false)]','(Delivery::TrailingBurst,false),(Delivery::TrailingBurst,true)]')
s=s.replace('    for (hit, _) in hits {','    for (hit, voice) in hits {')
s=s.replace('            attacks[near].push(late);','''            attacks[near].push(late);
            eprintln!("ASSIGN,{from},{to},{transition},{mode:?},{comparator},{near},{},{hit},{late},{},{}",expected[near],voice.len(),voice==baseline);''')
s=s.replace('    Observation { attacks, unmatched, malformed, steps, dropouts }','''    for (i,slots) in attacks.iter().enumerate() {
        if slots.is_empty() {eprintln!("ASSIGN,{from},{to},{transition},{mode:?},{comparator},{i},{},,,,",expected[i]);}
    }
    Observation { attacks, unmatched, malformed, steps, dropouts }''')
f.write_text(s,encoding='utf-8')
