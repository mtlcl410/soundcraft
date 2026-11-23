#[test]
#[ignore = "20 five-to-seven-minute tracks at 48 kHz; run serially"]
fn twenty_full_length_dj_tracks_preserve_the_recorded_eighths_through_transitions() {
    let bpms = [118.,124.,130.,136.,142.,148.,142.,136.,130.,124.,118.,124.,130.,136.,142.,148.,142.,136.,130.,124.];
    let mut ideal = Vec::new();
    let mut exclude = Vec::new();
    let mut burst = 0..0;
    let mut time=0_f64;
    for (track,&tempo) in bpms.iter().enumerate() {
        let seconds=303.+((track*37)%101) as f64;
        let bars=(seconds*tempo/240.).ceil() as usize;
        let length=bars*96;
        let start=ideal.len();
        let blend=length-16*96;
        let next=bpms.get(track+1).copied().unwrap_or(tempo);
        let special=32*96;
        for p in 0..length {
            let bpm=if track==7 && (special..special+48).contains(&p) {
                let k=p-special;
                if k<24 {tempo*(5_f64/tempo).powf((k+1) as f64/24.)}
                else {5.*(tempo/5.).powf((k-23) as f64/24.)}
            } else if track==12 && (special..special+16*96).contains(&p) {
                tempo/2.
            } else if p>=blend {
                tempo+(next-tempo)*(p-blend) as f64/(length-blend) as f64
            } else {tempo};
            ideal.push(time.round() as i64);
            if ideal.len()%12==1 {
                let pickup=track==0 && p<48;
                let mixing=track+1<bpms.len() && p>=blend;
                let braking=track==7 && (special..special+96).contains(&p);
                let half_step=track==12 && ((special..special+48).contains(&p) || (special+16*96..special+16*96+48).contains(&p));
                exclude.push(pickup || mixing || braking || half_step);
            }
            time+=period(bpm);
        }
        if track==5 {burst=start+special..start+special+16*96;}
    }
    let mut arrived=jitter(&ideal,1000,71);
    let mut head=burst.start;
    let mut width=3;
    while head<burst.end {
        let end=(head+width).min(burst.end);
        let last=arrived[end-1];
        for (i,t) in arrived[head..end].iter_mut().enumerate() {*t=last+i as i64*200;}
        width=if width==5 {3} else {width+1};
        head=end;
    }
    let r=render_dj(bpms[0],&ideal,&arrived,Ending::Release);
    let signed=errors("20 tracks; 16-bar blends; seeded jitter; brake, half-time and causal bursts",&r);
    assert_eq!(signed.len(),exclude.len());
    let mut stable:Vec<_>=signed.iter().zip(&exclude).filter(|(_,skip)|!**skip).map(|(x,_)|x.abs()).collect();
    stable.sort_unstable();
    let p999=stable[(stable.len()*999).div_ceil(1000)-1];
    eprintln!("20 tracks, {} eighths, {} outside transitions, p99.9 {p999} samples, {} grid events",signed.len(),stable.len(),r.tempo_events);
    assert!(p999<=192);
}
