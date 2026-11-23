use super::*;
use serde_json::json;

#[test]
fn scenario_d7_corrupt_sync_settings_recover_independently_with_diagnostics(){
    let dir=std::env::temp_dir().join(format!("g11-pref-probe-{}",std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path=dir.join("ui.json");
    let mut base=serde_json::to_value(soundcraft_ui_egui::UiState::default()).unwrap();
    base["narrow_mix"]=json!(true);base["midi_sync"]["ports"]["DIN"]=json!({"enabled":false,"in_offset_samples":0,"out_offset_samples":0});
    let mut misses=Vec::new();
    for (owner,key,v) in [
        (1662,"/midi_sync/enabled",json!(7)),(1662,"/midi_sync/compensation/beat_clock",json!("no")),
        (1662,"/midi_sync/compensation/notes",json!([])),(1662,"/midi_sync/ports/DIN/enabled",json!("yes")),
        (1662,"/midi_sync/ports/DIN/out_offset_samples",json!(i64::MAX)),
        (1662,"/midi_sync/ports/DIN/in_offset_samples",json!(i64::MIN)),
        (1663,"/gen_mtc",json!({})),(1663,"/mtc_input_port",json!(99)),(1663,"/mtc_output_port",json!([])),
        (1663,"/midi_sync/compensation/mtc",json!({})),
        (1669,"/clock_follow_input",json!([13])),(1669,"/clock_follow_stop_on_loss",json!("stop")),
        (1669,"/clock_follow_input_offsets",json!({"DIN":"-bad"}))]{
        let mut j=base.clone();
        let k=key.strip_prefix('/').unwrap();
        if let Some(slot)=j.pointer_mut(key){*slot=v;}else{assert!(!k.contains('/'));j[k]=v;}
        let bytes=serde_json::to_vec(&j).unwrap();
        std::fs::write(&path,&bytes).unwrap();
        match load_ui(&path){
            Ok(Some(ui))=>{eprintln!("D7 {owner} {key} loaded other={} note={:?}",ui.narrow_mix,ui.status);if !ui.narrow_mix || ui.status.is_empty(){misses.push(key);}}
            other=>{eprintln!("D7 {owner} {key} load error={:?}, startup uses whole defaults",other.err());misses.push(key);}
        }
        assert_eq!(std::fs::read(&path).unwrap(),bytes);
    }
    std::fs::remove_dir_all(dir).unwrap();
    assert!(misses.is_empty(),"settings missing independent recovery or visible note: {misses:?}");
}
