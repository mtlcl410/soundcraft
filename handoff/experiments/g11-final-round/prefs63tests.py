from pathlib import Path
p=Path('crates/engine/src/cmd/options.rs')
s=p.read_text(encoding='utf-8')
where='    #[test]\n    fn existing_offset_and_freewheel_preferences'
assert where in s
s=s.replace(where,'''    #[test]
    fn loading_project_mtc_settings_resets_only_invalid_fields_with_a_message() {
        let mut source = Engine::default();
        source.execute("track.new", &json!({"count": 2})).unwrap();
        source.execute("setup.session", &json!({"freewheel":"jam_sync","freewheel_frames":17,"external_offset_frames":-3})).unwrap();
        let base = source.session();
        let mode_key = "midi.mtc.freewheel_mode";
        let frames_key = "midi.mtc.freewheel_frames";
        let offset_key = "sync.external_offset";
        for (field, expected_value, expected_mode, expected_frames) in [
            (frames_key, base.edit.value(offset_key,0.), "jam_sync", 8),
            (mode_key, base.edit.value(offset_key,0.), "frames", 17),
            (offset_key, 0., "jam_sync", 17),
        ] {
            let mut session = base.clone();
            if field == mode_key {
                session.edit.flags.remove("midi.mtc.freewheel_mode=jam_sync");
                session.edit.flags.insert("midi.mtc.freewheel_mode=unknown".into());
            } else {
                let bad = if field == offset_key { session.sample_rate.samples(3600.) as f64 + 1. } else { 512. };
                session.edit.values.insert(field.into(), bad);
            }
            let loaded = soundcraft_model::Session::from_json(&session.to_json().unwrap()).unwrap();
            for engine in [Engine::new(loaded.clone()), {
                let mut engine = Engine::default();
                engine.replace_session(loaded.clone());
                engine
            }] {
                assert_eq!(engine.mtc_freewheel_frames(), expected_frames, "{field}");
                assert_eq!(engine.mtc_freewheel_mode(), expected_mode, "{field}");
                assert_eq!(engine.session().edit.value(offset_key,0.), expected_value, "{field}");
                assert_eq!(serde_json::to_value(&engine.session().tracks).unwrap(), serde_json::to_value(&base.tracks).unwrap());
                assert_eq!(engine.messages.iter().filter(|m| m.contains(field)).count(), 1, "{field}: {:?}",engine.messages);
                assert!(Engine::new(engine.session().clone()).messages.is_empty(), "resolved setting should survive reopen");
            }
        }
    }

    #[test]
    fn existing_offset_and_freewheel_preferences''',1)
p.write_text(s,encoding='utf-8')
