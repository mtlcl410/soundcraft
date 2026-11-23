from pathlib import Path
def add(path,text):
 p=Path(path);p.write_text(p.read_text(encoding="utf8")+text,encoding="utf8")
def insert(path,mark,text):
 p=Path(path);s=p.read_text(encoding="utf8");assert s.count(mark)==1; p.write_text(s.replace(mark,text+mark),encoding="utf8")
add("crates/playback/src/tests.rs",r'''
#[cfg(any(target_os = "linux", target_os = "macos", target_os = "windows"))]
#[test]
fn retained_audio_uses_its_render_rate_until_the_generation_boundary() {
    use crate::sync_clock::{DeviceTiming, Publisher, View};
    use std::time::{Duration, Instant};
    let (_, mut state, tx, track) = spike_session(0);
    let view = View::default();
    tx.send(Cmd::Clock(Some(Publisher::new(view.clone(), Arc::default())))).unwrap();
    let start = Instant::now();
    let timing = |frame| DeviceTiming::new(start, Some(Duration::ZERO), frame);
    state.device_timing = Some(timing(0));
    state.fill(&mut [0.;1200], 2);
    let mut next = (*state.session).clone();
    next.sample_rate = soundcraft_time::SampleRate::new(96_000).unwrap();
    next.track_mut(track).unwrap().playlist_mut().unwrap().clips.clear();
    tx.send(Cmd::Session(2, Arc::new(next), vec![])).unwrap();
    let mut audio = [0.;1200];
    for (a,b) in [(0,128),(128,600)] {
        state.device_timing = Some(timing(600+a));
        state.fill(&mut audio[2*a..2*b],2);
    }
    assert!(audio[..848].iter().step_by(2).all(|v| v.abs()>0.001), "all 424 retained frames must play");
    assert!(audio[848..].iter().all(|v| v.abs()<0.00001));
    for (frame,rate) in [(600,48_000.),(1023,48_000.),(1024,96_000.)] {
        let b=view.lock().unwrap().read(timing(frame).heard_instant(48_000.,0),true,0).0.unwrap();
        assert_eq!(b.samples_per_second,rate);
    }
}

#[cfg(any(target_os = "linux", target_os = "macos", target_os = "windows"))]
#[test]
fn a_stopped_locate_while_monitoring_publishes_the_transport_position() {
    use crate::sync_clock::{DeviceTiming, Publisher, View};
    use std::time::{Duration,Instant};
    let (mut state,tx,_,_,_) = keyboard_session();
    let view=View::default();
    tx.send(Cmd::Clock(Some(Publisher::new(view.clone(),Arc::default())))).unwrap();
    let now=Instant::now();
    state.device_timing=Some(DeviceTiming::new(now,Some(Duration::ZERO),0));
    state.fill(&mut [0.;1200],2);
    tx.send(Cmd::Locate(42_000)).unwrap();
    state.device_timing=Some(DeviceTiming::new(now,Some(Duration::ZERO),600));
    state.fill(&mut [0.;128],2);
    let block=view.lock().unwrap().read(now+Duration::from_millis(13),true,0).0.unwrap();
    assert!(!block.playing);
    assert_eq!((block.sample,block.origin),(42_000.,42_000));
}

#[test]
fn rejected_online_recording_cannot_leak_a_tentative_note_into_the_next_take() {
    let (mut state,tx,feed,..)=keyboard_session();
    tx.send(Cmd::Play {from:0,end:None,looped:None}).unwrap();
    state.fill(&mut [0.;128],2);
    feed.begin_pass();
    feed.set_mtc_source(Some(1));
    feed.receive(0,&[0x90,60,100]);
    tx.send(Cmd::Recording(true,0)).unwrap();
    state.fill(&mut [0.;128],2);
    assert!(!feed.begin_pending());
    feed.set_mtc_source(None);
    let mut events=Vec::new();
    feed.take_recorded(&mut events);
    assert!(events.is_empty(),"{events:?}");
}
''')
insert("crates/engine/src/cmd/options.rs","    #[test]\n    fn new_session_starts_at_one_hour",r'''    #[test]
    fn explicitly_resetting_a_conflicting_external_offset_survives_reopen() {
        for (cmd,args) in [
            ("setup.session",json!({"external_offset_frames":0})),
            ("setup.external_timecode_offset",json!({"samples":0})),
            ("setup.external_timecode_offset",json!({"frames":0})),
            ("setup.external_timecode_offset",json!({"timecode":"00:00:00:00"})),
        ] {
            let mut s=Engine::default().session().clone();
            s.edit.values.insert("sync.external_offset".into(),42.);
            s.edit.values.insert("midi.mtc.external_offset_frames".into(),100.);
            let mut e=Engine::new(s);
            e.execute(cmd,&args).unwrap();
            let reopened=Engine::new(e.session().clone());
            assert_eq!(reopened.session().edit.value("sync.external_offset",0.),0.,"{cmd} {args}");
        }
    }

''')
p=Path("crates/ui-egui/src/app/mtc.rs");s=p.read_text(encoding="utf8");mark='        assert!(host.engine.transport.recording);\n        host.stop_play();';assert s.count(mark)==1;s=s.replace(mark,'''        assert!(host.midi_connected() && host.player.is_none());
        assert!(!host.engine.transport.recording, "a MIDI-only take needs a running audio callback");
        assert!(host.ui.status.contains("Playback Engine"));''');p.write_text(s,encoding="utf8")

