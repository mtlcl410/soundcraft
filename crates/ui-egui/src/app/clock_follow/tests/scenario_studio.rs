use super::*;
use soundcraft_model::{Insert, Session, SourceAudio, SourceId, TrackKind};
use soundcraft_time::Range;
use std::path::PathBuf;
use std::sync::Arc;

struct Scratch(PathBuf);
impl Scratch {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!("g11-studio-{}-{}", std::process::id(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for Scratch { fn drop(&mut self) { let _ = std::fs::remove_dir_all(&self.0); } }

struct Take { app: SoundApp, audio: TrackId, midi: TrackId, start: i64, length:i64, _dir: Scratch }
fn take(offset: i64, changing: bool) -> Take {
    let mut app = SoundApp::new(Default::default(),None,crate::Services::default());
    let dir = Scratch::new();
    let path = dir.0.join("Scenario.scraft");
    app.run("session.save_as",json!({"path":path})).unwrap();
    let audio = armed(&mut app,"audio");
    let midi = armed(&mut app,"midi");
    let (rec,mut capture) = Recorder::simulated_input();
    app.recorder=Some(rec);
    app.midi_inputs=Some(MidiInputs::with_port_names(vec![],vec!["DIN".into(),"Keys".into()]));
    app.run("setup.midi_clock_follow",json!({"enabled":true,"input":"DIN","input_offset_samples":offset})).unwrap();
    let feed=app.midi_inputs.as_ref().unwrap().feed().clone(); let port=feed.ports().assign("DIN"); let keys=feed.ports().assign("Keys");
    let mut us=0;
    for _ in 0..24 {feed.set_clock(us);feed.receive(port,&[0xf8]);us+=25000;}
    feed.set_clock(us);feed.receive(port,&[0xf2,16,0]);app.service_clock_follow();app.handle_transport(0.);
    feed.receive(port,&[0xfb,0xf8]);app.service_clock_follow();app.handle_transport(0.);
    app.run("transport.record",json!({})).unwrap();app.handle_transport(0.);
    let start=app.take_plan.as_ref().unwrap().start;
    let mut len=0;
    // The full take fits in the simulated input ring even if the writer thread has not run.
    for pulse in 0..36 {
        let frames=if changing && pulse>=18 {1000} else {1200};
        let mut block=vec![0.;frames];
        if [3,9,15,21,27,33].contains(&pulse) {block[0]=0.8;play_note(&mut app,keys,60);}
        capture(&block);app.handle_transport(frames as f32/48000.);
        len+=frames as i64;
        us=600000+len*1000000/48000;feed.set_clock(us);feed.receive(port,&[0xf8]);app.service_clock_follow();
    }
    feed.receive(port,&[0xfc]);app.service_clock_follow();app.handle_transport(0.);
    app.run("setup.midi_clock_follow",json!({"enabled":false})).unwrap();
    app.run("session.save",json!({})).unwrap();
    app.run("session.open",json!({"path":path})).unwrap();
    Take{app,audio,midi,start,length:len,_dir:dir}
}

// Render one stem at a time. Give recorded MIDI notes a one-sample click instrument
// for the measurement. Leave the recorded sequences, times and edited clips untouched.
fn attacks(t:&Take,id:TrackId,end:i64)->Vec<i64>{
    let mut s:Session=t.app.engine.session().clone();
    s.tracks.retain(|tr| tr.id==id);
    if id==t.midi {
        let src=SourceId(30000);
        let mut click=vec![0.;256]; click[0]=1.;
        s.pool.insert(src,Arc::new(SourceAudio::new(craft_audio::AudioBuffer{sample_rate:48000,channels:vec![click]})));
        let tr=s.track_mut(id).unwrap();
        tr.kind=TrackKind::Instrument;
        let mut ins=Insert::new("sampler"); ins.sample=Some(src); ins.params.insert("attack".into(),0.);ins.params.insert("root_note".into(),60.);
        tr.instrument=Some(ins);
    }
    let y=soundcraft_mix::render_range(&s,Range::new(0,end),128);
    y[0].iter().enumerate().filter(|(i,v)| v.abs()>1e-7 && (*i==0 || y[0][*i-1].abs()<=1e-7)).map(|(i,_)|i as i64).collect()
}
fn measure(t:&Take,stage:&str,end:i64,expected:usize)->bool{
    let a=attacks(t,t.audio,end); let m=attacks(t,t.midi,end);
    let delta:Vec<_>=a.iter().zip(&m).map(|(a,m)|m-a).collect();
    eprintln!("STUDIO {stage} audio={a:?} midi={m:?} diff={delta:?}");
    a.len()==expected && m.len()==expected && delta.iter().all(|v|v.abs()<=1)
}
#[test]
fn scenario_b6_record_tempo_change_and_reopen(){
    let t=take(0,true);
    assert!(measure(&t,"B6",t.start+t.length,6));
}
#[test]
fn scenario_d6_calibrated_recording_position(){
    let mut starts=Vec::new();
    for offset in [-12000,0,12000] {
        let t=take(offset,false);
        let a=attacks(&t,t.audio,t.start+t.length);
        let m=attacks(&t,t.midi,t.start+t.length);
        eprintln!("STUDIO D6 offset={offset} start={} a={a:?} m={m:?}",t.start);
        assert_eq!(a.len(),6);assert_eq!(m.len(),6);
        starts.push((a[0],m[0]));
    }
    assert_eq!((starts[0].0-starts[1].0,starts[0].1-starts[1].1),(12000,12000));
    assert_eq!((starts[2].0-starts[1].0,starts[2].1-starts[1].1),(-12000,-12000));
}
#[test]
fn scenario_d1_reopened_recording_survives_edits(){
    let mut t=take(0,false);let start=t.start;let len=t.length;let end=start+len;let ids=[t.audio.0,t.midi.0];
    let mut all=measure(&t,"reopen",end,6);
    for (op,args,stage,until,n) in [
       ("edit.separate",json!({"tracks":ids,"at":start+len/2}),"split",end,6),
       ("edit.heal",json!({"tracks":ids,"start":start,"end":end}),"heal",end,6),
       ("edit.copy",json!({"tracks":ids,"start":start,"end":end}),"copy",end,6),
       ("edit.paste",json!({"tracks":ids,"at":end}),"paste",end+len,12),
       ("edit.consolidate",json!({"tracks":ids,"start":start,"end":end+len}),"consolidate",end+len,12),
    ] {
        let result=t.app.run(op,args); eprintln!("STUDIO D1 {op} {result:?}");
        all &= result.is_ok() && measure(&t,stage,until,n);
    }
    for id in [t.audio,t.midi] {
        let cs=t.app.engine.session().track(id).unwrap().clips();
        if cs.len()!=1 {eprintln!("STUDIO loop track has {} clips",cs.len());all=false;}
        if let Some(c)=cs.first() {let result=t.app.run("clip.loop",json!({"clip":c.id.0,"count":2}));eprintln!("STUDIO loop {result:?}");all &=result.is_ok();}
    }
    all &= measure(&t,"loop",start+4*len,24);assert!(all);
}

#[test]
fn scenario_c8_follow_offset_across_sample_rates() {
    let mut host = SoundApp::new(Default::default(),None,crate::Services::default());
    host.midi_inputs = Some(MidiInputs::with_port_names(vec![], vec!["DIN".into()]));
    host.run("setup.midi_clock_follow", json!({"input":"DIN","input_offset_samples":4800})).unwrap();
    for rate in [44100,48000,96000,192000] {
        host.engine.session_mut().sample_rate = soundcraft_time::SampleRate::new(rate).unwrap();
        let res = host.run("setup.midi_clock_follow", json!({})).unwrap();
        let samples = res["input_offset_samples"].as_i64().unwrap();
        eprintln!("C8 follow rate={rate} stored={samples} ms={:.3}",samples as f64*1000./rate as f64);
        assert_eq!(samples,4800);
    }
}
