use super::sampler_song::sampler_song;
use super::*;
use soundcraft_model::ClipContent;
use std::io::{BufWriter, Write};

#[test]
#[ignore = "Local simulated 20-song PCM audit; set SOUNDCRAFT_DJ_LONG_DIR"]
fn dj_twenty_songs() {
    let dir = std::path::PathBuf::from(std::env::var("SOUNDCRAFT_DJ_LONG_DIR").unwrap());
    let rates = [118., 125., 132., 120., 126., 119., 131., 122., 128., 121.,
                 130., 123., 129., 118., 132., 124., 127., 119., 131., 120.];
    let sr = SampleRate::HZ_48000;
    let mut schedule = Vec::new();
    for (i, &bpm) in rates.iter().enumerate() {
        for _ in 0..32*96 { schedule.push((i+1, "song", bpm)); }
        if let Some(&next) = rates.get(i+1) {
            let bars = if i % 2 == 0 { 16 } else { 32 };
            for p in 0..bars*96 {
                schedule.push((i+1, "transition", bpm + (next-bpm)*p as f64/(bars*96) as f64));
            }
        }
    }
    let inputs = MidiInputs::with_port_names(vec![],vec!["DJ".into()]);
    let feed = inputs.feed();
    let port = feed.ports().assign("DJ");
    feed.set_clock_follow(Some(port),true,0,false);
    feed.set_clock(0);
    feed.receive(port,&[0xfa]);
    let mut actions = Vec::new();
    let mut song = sampler_song(TempoMap::new(rates[0],4,4).unwrap(),sr,64,48_000*4000);
    let mut mix = soundcraft_mix::MixEngine::new(48_000.,128);
    let mut block = vec![vec![0.;128];2];
    let mut expected = Vec::new();
    let mut hits = Vec::new();
    let (mut ref_wave,mut voice)=(Vec::<f32>::new(),Vec::<f32>::new());
    let (mut start,mut pos,mut false_steps,mut step)=(0_i64,0_i64,0,false);
    let mut stamp=0.0_f64;
    let count = schedule.len()/12;
    // Four bars of past notes and four bars of future notes overlap each window.
    // Only the score fixture is paged; the clock, tempo map and mixer never reset.
    for (p,&(song_nr,kind,bpm)) in schedule.iter().enumerate() {
        if p%384==0 {
            let base=(p/12).saturating_sub(16);
            let ClipContent::Midi{sequence}=&mut song.tracks[0].playlist_mut().unwrap().clips[0].content else {unreachable!()};
            sequence.notes.truncate(count.saturating_sub(base));
            for (n,note) in sequence.notes.iter_mut().enumerate() { note.start=((base+n)*480) as i64; }
        }
        let at=sr.samples(stamp/1e6);
        if p%12==0 {expected.push((at,song_nr,kind,bpm));}
        feed.set_clock(stamp.round() as i64);
        feed.receive(port,&[0xf8]);
        let snap=feed.clock_follow_status(&mut actions);
        false_steps+=usize::from(snap.recovering_tempo_step && !step);
        step=snap.recovering_tempo_step;
        update_grid(&mut song.tempo,Some((0,0)),0,snap,sr,at+1440);
        stamp+=2_500_000./bpm;
        let end=sr.samples(stamp/1e6) + if p+1==schedule.len() {4800} else {0};
        while pos<end {
            let n=(end-pos).min(128) as usize;
            mix.render_with_clock_limit(&song,pos,n,&mut block,feed.clock_render_tick());
            for (j,&s) in block[0][..n].iter().enumerate() {
                if s.abs()>0.001 {
                    if voice.is_empty(){start=pos+j as i64;}
                    voice.push(s);
                } else if !voice.is_empty() {
                    if ref_wave.is_empty(){ref_wave=voice.clone();}
                    hits.push((start,voice.len(),voice==ref_wave && voice.len()==96));
                    voice.clear();
                }
            }
            pos+=n as i64;
        }
    }
    let mut csv=BufWriter::new(std::fs::File::create(dir.join("eighths.csv")).unwrap());
    writeln!(csv,"eighth,song,phase,bpm,expected_sample,actual_sample,delta_samples,delta_ms,tail_samples,waveform_exact").unwrap();
    let (mut missing,mut extra,mut damaged,mut idx,mut peak)=(0,0,0,0,0);
    for (i,&(at,song,kind,bpm)) in expected.iter().enumerate(){
        let until=expected.get(i+1).map_or(i64::MAX,|next|(at+next.0)/2);
        let mut n=0;
        while idx<hits.len() && hits[idx].0<until {
            let (actual,tail,ok)=hits[idx];
            let err=actual-at;
            peak=peak.max(err.abs());
            damaged+=usize::from(!ok);
            writeln!(csv,"{i},{song},{kind},{bpm:.6},{at},{actual},{err},{:.6},{tail},{ok}",err as f64/48.).unwrap();
            idx+=1; n+=1;
        }
        if n==0 {missing+=1;writeln!(csv,"{i},{song},{kind},{bpm:.6},{at},,,,,").unwrap();}
        if n>1 {extra+=n-1;}
    }
    csv.flush().unwrap();
    eprintln!("20SONGS duration_s={:.3} bars={} attacks={}/{} missing={missing} duplicate={extra} damaged={damaged} trailing_open={} peak_ms={:.6} false_steps={false_steps} tempo_events={}",stamp/1e6,schedule.len()/96,hits.len(),expected.len(),!voice.is_empty(),peak as f64/48.,song.tempo.tempos().len());
    assert_eq!((missing,extra,damaged,false_steps,voice.len()),(0,0,0,0,0));
}
