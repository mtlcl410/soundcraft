use super::*;
use super::sampler_song::sampler_song;
use soundcraft_model::ClipContent;
use std::io::{BufWriter, Write};

// Local audit. Stream the full eight hours through the sampler; retain only each
// finished attack and its reference. Rotate the score window between eighths.
#[test]
fn audit_eight_hour_pcm() {
    let sr = SampleRate::HZ_48000;
    let inputs = MidiInputs::with_port_names(vec![],vec!["clock".into()]);
    let feed = inputs.feed();
    let port = feed.ports().assign("clock");
    feed.set_clock_follow(Some(port),true,0,false);
    feed.set_clock(0);
    feed.receive(port,&[0xfa]);
    let mut actions=Vec::new();
    let mut song=sampler_song(TempoMap::default(),sr,16,48_000*28_810);
    let mut mixer=soundcraft_mix::MixEngine::new(48_000.,1024);
    let mut block=vec![vec![0.;1024];2];
    let mut expected=Vec::new();
    let mut hits=Vec::new();
    let mut reference=Vec::new();
    let mut voice=Vec::new();
    let mut onset=0;
    let mut pos=0_i64;
    let mut stamp=0.;
    let mut pulse=0;
    let mut grid_peak=0;
    let mut fast=false;
    let mut entries=0;
    loop {
        let time=stamp as f64;
        let at=sr.samples(time/1e6);
        feed.set_clock(time.round() as i64);
        feed.receive(port,&[0xf8]);
        if pulse%12==0 {expected.push(at);}
        if pulse%6==0 {
            let snapshot=feed.clock_follow_status(&mut actions);
            if snapshot.recovering_tempo_step && !fast {entries+=1;}
            fast=snapshot.recovering_tempo_step;
            update_grid(&mut song.tempo, Some((0,0)),0,snapshot,sr,at+1200);
            grid_peak=std::cmp::max(grid_peak,song.tempo.tick_to_samples(pulse*TICKS_PER_PULSE,sr).abs_diff(at));
        }
        if pulse%(16*12)==16*12-6 {
            let ClipContent::Midi{sequence}=&mut song.tracks[0].playlist_mut().unwrap().clips[0].content else {unreachable!()};
            for note in &mut sequence.notes {note.start+=16*480;}
        }
        let done=time>=28_800_000_000.;
        let bpm=120.0 + 0.2*(time/30_000_000.*std::f64::consts::TAU).sin();
        stamp+=2_500_000./bpm;
        let end=if done {at+4800} else {sr.samples(stamp/1e6)};
        while pos<end {
            let frames=(end-pos).min(1024) as usize;
            mixer.render_with_clock_limit(&song,pos,frames,&mut block,feed.clock_render_tick());
            for (j,s) in block[0][..frames].iter().enumerate() {
                if s.abs()>0.001 {
                    if voice.is_empty(){onset=pos+j as i64;}
                    voice.push(*s);
                } else if !voice.is_empty() {
                    if reference.is_empty() { reference=voice.clone(); }
                    assert_eq!(reference,voice,"waveform at {onset}");
                    hits.push((onset,voice.len()));
                    voice.clear();
                }
            }
            pos+=frames as i64;
        }
        if done {break;}
        pulse+=1;
    }
    assert!(voice.is_empty());
    assert_eq!(reference.len(),96);
    assert_eq!(hits.len(),expected.len());
    let mut csv=BufWriter::new(std::fs::File::create(std::env::var("SOUNDCRAFT_FLUTTER_CSV").unwrap()).unwrap());
    writeln!(csv,"eighth,expected_sample,onset_sample,delta_samples,tail_samples").unwrap();
    let mut peak=0;
    for (i,(expected,(actual,tail))) in expected.iter().zip(&hits).enumerate(){
        let err=actual-expected;
        peak=peak.max(err.abs());
        writeln!(csv,"{i},{expected},{actual},{err},{tail}").unwrap();
    }
    eprintln!("8H_PCM count={} peak_samples={} grid_peak_samples={} false_step_entries={} tail_samples={} tempo_events={}",hits.len(),peak,grid_peak,entries,reference.len(),song.tempo.tempos().len());
    assert_eq!(entries,0);
}
