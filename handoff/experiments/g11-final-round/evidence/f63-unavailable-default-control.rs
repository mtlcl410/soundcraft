    #[cfg(any(target_os = "windows", target_os = "linux", target_os = "macos"))]
    #[test]
    fn silent_clock_does_not_become_the_default_output_reconnect_target() {
        let mut app = SoundApp::new(crate::Engine::default(), None, crate::Services::default());
        let player = Player::reconnect_output(app.engine.session_arc(), &app.ui.audio, "nonexistent recovery test output");
        assert!(player.silent);
        let inputs = soundcraft_playback::midi::MidiInputs::with_port_names(vec![], vec!["MTC".into()]);
        let feed = inputs.feed();
        feed.set_mtc_source(Some(feed.ports().assign("MTC")));
        player.set_midi(feed.clone());
        assert_eq!(player.midi_sync_status().lead_source, soundcraft_playback::OutputLeadSource::Unobserved);
        assert_eq!(player.output_timing_issue(), None);
        app.player = Some(player);
        assert_eq!(app.recovery_output(), None, "retry system default after a failed Apply");
    }

