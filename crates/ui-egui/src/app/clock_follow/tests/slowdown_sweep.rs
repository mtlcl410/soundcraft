use super::sampler_song::sampler_song;
use super::*;
use soundcraft_model::{ClipContent,Session};
use soundcraft_mix::MixEngine;
use std::io::{BufWriter,Write};
const SR: i64 = 48_000;
fn us(pos:i64)->i64 {(pos*1_000_000+SR/2)/SR}
fn runs(pcm:&[f32])->Vec<(usize,usize)> {
    let mut hits:Vec<(usize,usize)>=vec![];
    for (i,v) in pcm.iter().enumerate() {
        if v.abs()>1e-10 {
            if let Some(last)=hits.last_mut() && i-last.1<=12 {last.1=i+1;} else {hits.push((i,i+1));}
        }
    }
    hits
}
fn click_template(pulse:i64)->Vec<f32> {
    let sr=SampleRate::HZ_48000;
    let mut s=Session{sample_rate:sr,tempo:TempoMap::new(120.,4,4).unwrap(),..Default::default()};
    s.edit.click=true;
    let mut mix=MixEngine::new(48_000.,2048);mix.metronome=true;
    let mut b=vec![vec![0.;2048];2];
    mix.render(&s,1000*pulse,2048,&mut b);
    let (l,r)=runs(&b[0])[0];b[0][l..r].to_vec()
}
#[test]
fn audit_slowdown_device_phase_sweep() {
    let path=std::env::var("SOUNDCRAFT_SWEEP_CSV").unwrap();
    let predict=std::env::var("SOUNDCRAFT_SWEEP_POLICY").unwrap()=="predict";
    let mut file=BufWriter::new(std::fs::File::create(path).unwrap());
    writeln!(file,"from_bpm,to_bpm,buffer,lead_ms,cut_pulse,callback_phase_samples,stem,event_pulse,ref_sample,actual_sample,err_samples,tail_samples,waveform_ok,slot_count,first_offbeat_pulse,first_beat_pulse").unwrap();
    let norm=click_template(24);
    let accent=click_template(0);
    let sr=SampleRate::HZ_48000;
    for bpm in [200_i64,240,300] {
        let old=SR*60/(bpm*24); let new=old*5/4;
        for buffer in [128_usize,512,2048] {
            for lead_ms in [30_i64,50] {
                for cut in 384_i64..408 {
                    let time=|p:i64| p.min(cut)*old + (p-cut).max(0)*new;
                    for phase in [0,buffer/4,buffer/2,3*buffer/4] {
                        let inputs=MidiInputs::with_port_names(vec![],vec!["wire".into()]);
                        let feed=inputs.feed();let port=feed.ports().assign("wire");
                        feed.set_clock_follow(Some(port),true,0,false);feed.set_clock(0);feed.receive(port,&[0xfa]);
                        let mut actions=Vec::new();
                        let mut song=sampler_song(TempoMap::new(bpm as f64,4,4).unwrap(),sr,11,time(480)+48000);
                        let ClipContent::Midi{sequence}=&mut song.tracks[0].playlist_mut().unwrap().clips[0].content else {unreachable!()};
                        for note in &mut sequence.notes {note.start+=360*TICKS_PER_PULSE;}
                        let mut click=Session {tempo:song.tempo.clone(),sample_rate:sr,..Default::default()};click.edit.click=true;
                        let mut hats=MixEngine::new(48_000.,512);let mut metro=MixEngine::new(48_000.,512);metro.metronome=true;
                        let mut a=vec![vec![0.;512];2];let mut b=a.clone();
                        let first_cb=time(336)+phase as i64;
                        let first_pos=first_cb+lead_ms*48;
                        let mut cb=first_cb;let mut pulse=0_i64;
                        let mut stems=[Vec::new(),Vec::new()];
                        while cb+lead_ms*48 < time(480)+48*160 {
                            let pos=cb+lead_ms*48;
                            while time(pulse)<=cb {
                                let t=time(pulse);feed.set_clock(us(t));feed.receive(port,&[0xf8]);
                                let snap=feed.clock_follow_status(&mut actions);actions.clear();
                                // UI handles each wire pulse; the last device callback has
                                // committed all samples before pos. Same guard as the live app.
                                let guard=sr.samples((2.5/snap.bpm.unwrap_or(120.)).max(buffer as f64/SR as f64));
                                if update_grid(&mut song.tempo,Some((0,0)),0,snap,sr,if t>=first_cb {pos+guard}else{0}){
                                    click.tempo=song.tempo.clone();
                                }
                                pulse+=1;
                            }
                            feed.set_clock(us(cb));
                            for sub in (0..buffer).step_by(512) {
                                let n=(buffer-sub).min(512);
                                let at=pos+sub as i64;
                                let limit=if predict {feed.clock_render_tick()} else {feed.clock_render_tick()};
                                hats.render_with_clock_limit(&song,at,n,&mut a,limit);
                                metro.render_with_clock_limit(&click,at,n,&mut b,limit);
                                stems[0].extend_from_slice(&a[0][..n]);stems[1].extend_from_slice(&b[0][..n]);
                            }
                            cb+=buffer as i64;
                        }
                        for (i,pcm) in stems.iter().enumerate() {
                            let hits=runs(pcm);
                            let first_off=if cut%24<12 {cut/24*24+12}else{cut/24*24+36};
                            let first_beat=(cut/24+1)*24;
                            let stride=if i==0 {12}else{24};
                            let expected:Vec<_>=(360..=480).step_by(stride).collect();
                            let mut slots=vec![Vec::new();expected.len()];
                            let voice=hits.first().map(|&(s,e)|&pcm[s..e]).unwrap_or(&[]);
                            for &(s,e) in &hits{
                                let onset=s as i64+first_pos-if i==1 {1}else{0};
                                let idx=(0..expected.len()).min_by_key(|&j|onset.abs_diff(time(expected[j]))).unwrap();
                                let template=if i==0 {voice} else if expected[idx]%96==0 {&accent} else {&norm};
                                slots[idx].push((onset,e-s,&pcm[s..e]==template && (i!=0 || template.len()==96)));
                            }
                            for (j,slot) in slots.iter().enumerate(){
                                let p=expected[j];let t=time(p);
                                let stem=if i==0 {"hat"}else{"click"};
                                if slot.is_empty() {writeln!(file,"{bpm},{},{buffer},{lead_ms},{cut},{phase},{stem},{p},{t},,,,false,0,{first_off},{first_beat}",bpm*4/5).unwrap();}
                                for (actual,tail,ok) in slot {writeln!(file,"{bpm},{},{buffer},{lead_ms},{cut},{phase},{stem},{p},{t},{actual},{},{tail},{ok},{},{first_off},{first_beat}",bpm*4/5,actual-t,slot.len()).unwrap();}
                            }
                        }
                    }
                }
                eprintln!("completed {bpm} / {buffer} / {lead_ms} / predict={predict}");
            }
        }
    }
}
