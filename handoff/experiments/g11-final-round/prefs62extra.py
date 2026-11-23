from pathlib import Path
p=Path("apps/soundcraft/src/config.rs")
s=p.read_text()
key='        std::fs::remove_file(path).unwrap();\n    }\n\n    #[test]\n    fn native_file_reload'
s=s.replace(key,'''        save_ui(&path, &ui).unwrap();
        let reloaded = load_ui(&path).unwrap().unwrap();
        assert!(reloaded.status.is_empty());
        assert_eq!(reloaded.midi_sync, ui.midi_sync);
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn midi_sync_pref_recovery_validates_each_saved_identity_and_preserves_known_fields() {
        let mut saved = serde_json::json!({"midi_sync":{
            "ports":{"Keys":{"enabled":true,"offset_samples":10000001,"newer_field":true}},
            "port_ids":{"Good":"driver-id","Broken":42," ":"bad name"}
        }});
        let mut resets = Vec::new();
        recover_sync_settings(saved.as_object_mut().unwrap(), &mut resets);
        assert_eq!(saved["midi_sync"]["port_ids"], serde_json::json!({"Good":"driver-id"}));
        assert_eq!(saved["midi_sync"]["ports"]["Keys"], serde_json::json!({"enabled":true}));
        assert_eq!(resets.len(), 4);
    }

    #[test]
    fn native_file_reload''',1)
p.write_text(s)
p=Path("apps/soundcraft/src/main.rs")
s=p.read_text().replace('            for f in &files {','''            let settings_notice = std::mem::take(&mut app.ui.status);
            for f in &files {''',1).replace('            // If the system menu bar','''            if !settings_notice.is_empty() {
                if !app.ui.status.is_empty() {
                    app.ui.status.push(' ');
                }
                app.ui.status.push_str(&settings_notice);
            }
            // If the system menu bar''',1)
p.write_text(s)
