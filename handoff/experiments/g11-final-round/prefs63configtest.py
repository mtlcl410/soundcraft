from pathlib import Path
p=Path('apps/soundcraft/src/config.rs')
s=p.read_text(encoding='utf8')
w='    #[test]\n    fn native_file_reload'
t='''    #[test]
    fn midi_sync_pref_mtc_fields_recover_independently_and_report_each_bad_value() {
        let path = std::env::temp_dir().join(format!("soundcraft-mtc-pref-recovery-{}.json", std::process::id()));
        for (field, bad) in [("gen_mtc", serde_json::json!("on")), ("mtc_input_port", serde_json::json!("  ")), ("mtc_output_port", serde_json::json!(5))] {
            let mut saved = serde_json::json!({"gen_mtc":true,"mtc_input_port":"Reader","mtc_output_port":"Generator","midi_sync":{"enabled":true}});
            saved[field] = bad;
            std::fs::write(&path, serde_json::to_vec(&saved).unwrap()).unwrap();
            let restored = load_ui(&path).unwrap().unwrap();
            assert!(restored.midi_sync.enabled);
            assert_eq!(restored.gen_mtc, field != "gen_mtc");
            assert_eq!(restored.mtc_input_port.as_deref(), (field != "mtc_input_port").then_some("Reader"));
            assert_eq!(restored.mtc_output_port.as_deref(), (field != "mtc_output_port").then_some("Generator"));
            assert!(restored.status.contains(field), "{}", restored.status);
        }
        std::fs::remove_file(path).unwrap();
    }

'''
assert w in s
p.write_text(s.replace(w,t+w,1),encoding='utf8')
