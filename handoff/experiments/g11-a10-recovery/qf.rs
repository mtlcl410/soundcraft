#[test]
fn recovered_mtc_locates_live_and_starts_a_complete_quarter_frame_group() {
    for (loss_ms, recovery_ms) in [(20, 50), (100, 200)] {
        let base = Instant::now();
        let mut song = Session::new("MTC recovery", soundcraft_time::SampleRate::HZ_48000);
        song.frame_rate = soundcraft_time::FrameRate::Fps25;
        song.timecode_start = 0;
        let mut routes = BTreeMap::new();
        set_route(&mut routes, 1, "desk".into(), Route { map: None, offset: 0, compensate: true, encoder: Box::<crate::mtc::Encoder>::default() });
        let capture = Arc::default();
        let port = routes.get_mut("desk").unwrap();
        port.link = Some(Capture(Arc::clone(&capture)));
        let view = View::default();
        let stats = Stats::default();
        let mut recovered = Vec::new();
        let mut pending = Vec::new();
        for ms in 0..=recovery_ms + 120 {
            let now = base + Duration::from_millis(ms);
            if ms % 10 == 0 {
                let lead = (!(loss_ms..recovery_ms).contains(&ms)).then_some(Duration::ZERO);
                view.lock().unwrap().push(Presentation { lead, ..super::tests::block(now, ms as f64 * 48., 480., Duration::ZERO) });
            }
            port.poll("desk", now, &song, &view, &stats, &mut pending);
            for (due, _, bytes) in capture.lock().unwrap().drain(..) {
                assert!(!(loss_ms..recovery_ms).contains(&ms));
                if ms >= recovery_ms {
                    assert_eq!(due, now);
                    recovered.push((ms, bytes));
                }
            }
        }
        let locate_frame = (recovery_ms / 40) as i64;
        assert_eq!(recovered[0], (recovery_ms, crate::mtc::locate(locate_frame, song.frame_rate).to_vec()));
        let group_ms = recovery_ms.div_ceil(80) * 80;
        for (piece, (ms, bytes)) in recovered[1..9].iter().enumerate() {
            assert_eq!(*ms, group_ms + 10 * piece as u64);
            assert_eq!(bytes.as_slice(), crate::mtc::quarters((group_ms / 40) as i64, song.frame_rate)[piece]);
        }
    }
}
