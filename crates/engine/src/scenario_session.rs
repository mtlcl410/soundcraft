use super::*;
use serde_json::{json,Value};
#[test]
fn scenario_d7_session_reload_recovers_sync_values_and_preserves_score(){
    let mut s=Session::default();
    s.name="Unrelated arrangement".into();
    s.add_track(soundcraft_model::TrackKind::Audio,soundcraft_model::ChannelFormat::Mono,Some("Backing".into()));
    let base:Value=serde_json::from_str(&s.to_json().unwrap()).unwrap();
    let dir=std::env::temp_dir().join(format!("g11-corrupt-session-{}",std::process::id()));std::fs::create_dir_all(&dir).unwrap();
    let path=dir.join("session.scraft");
    let mut misses=Vec::new();
    for (name,payload) in [("rate",json!("unrecognized rate")),("negative_frames",json!(-19)),("huge_frames",json!(1e20)),("wrong_type_frames",json!([8])),("offset",json!(1e22)),("unknown_mode",json!("midi.mtc.freewheel_mode=teleport")),("timecode_start",json!(true))]{
        let mut doc=base.clone();
        match name {
            "rate"=>doc["frame_rate"]=payload,
            "negative_frames"|"huge_frames"|"wrong_type_frames"=>doc["edit"]["values"]["midi.mtc.freewheel_frames"]=payload,
            "unknown_mode"=>doc["edit"]["flags"]=json!([payload]),
            "timecode_start"=>doc["timecode_start"]=payload,
            _=>doc["edit"]["values"]["sync.external_offset"]=payload
        }
        let bytes=serde_json::to_vec(&doc).unwrap();std::fs::write(&path,&bytes).unwrap();
        let mut engine=Engine::default();let opened=engine.execute("session.open",&json!({"path":path}));
        let score=engine.session().name=="Unrelated arrangement" && engine.session().tracks.iter().any(|t|t.name=="Backing");
        eprintln!("D7SESSION {name} score={score} open={opened:?} messages={:?} frames={} mode={}",engine.messages,engine.mtc_freewheel_frames(),engine.mtc_freewheel_mode());
        if !score || engine.messages.iter().all(|m|!(m.to_lowercase().contains("offset")||m.to_lowercase().contains("invalid")||m.to_lowercase().contains("freewheel")||m.to_lowercase().contains("rate"))) {misses.push(name);}
        assert_eq!(std::fs::read(&path).unwrap(),bytes);
    }
    std::fs::remove_dir_all(dir).unwrap();
    assert!(misses.is_empty(),"fields without independent recovery and warning {misses:?}");
}
