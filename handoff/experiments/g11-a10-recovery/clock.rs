#[test]
fn recovered_clock_repositions_before_the_next_sixteenth() {
    let base = Instant::now();
    let view = View::default();
    let song = Session::new("clock recovery", soundcraft_time::SampleRate::HZ_48000);
    let mut port = active_port(0, true);
    let stats = Stats::default();
    let mut pending = Vec::new();
    let mut recovered = Vec::new();
    for ms in 0..=300 {
        let now = base + Duration::from_millis(ms);
        if ms % 10 == 0 {
            let lead = (!(100..200).contains(&ms)).then_some(Duration::ZERO);
            view.lock().unwrap().push(Presentation { lead, ..block(now, ms as f64 * 48., 480., Duration::ZERO) });
        }
        port.poll("desk", now, &song, &view, &stats, &mut pending);
        for (due, msg) in port.link.as_mut().unwrap().messages.drain(..) {
            assert!(!(100..200).contains(&ms));
            if ms >= 200 {
                assert!(due <= now && now - due <= Duration::from_millis(1));
                recovered.push((ms, msg));
            }
        }
    }
    assert_eq!(recovered, [
        (200, vec![STOP]), (200, vec![0xf2, 2, 0]), (200, vec![CONTINUE]),
        (250, vec![CLOCK]), (271, vec![CLOCK]), (292, vec![CLOCK]),
    ]);
}

#[test]
fn a_missed_timing_gap_invalidates_only_the_compensated_route_queue() {
    let base = Instant::now();
    let view = View::default();
    let song = Session::default();
    let stats = Stats::default();
    let mut port = active_port(0, true);
    let delay = Duration::from_millis(20);
    for (index, compensate) in [true, false].into_iter().enumerate() {
        port.routes[index] = Some(Route { map: None, offset: 0, compensate,
            encoder: Box::new(Messages(vec![(delay, vec![0xf8])])) });
    }
    view.lock().unwrap().push(block(base, 0., 480., Duration::ZERO));
    port.poll("desk", base, &song, &view, &stats, &mut vec![]);
    // Both callback publications land between two worker polls.
    let now = base + delay;
    let mut timeline = view.lock().unwrap();
    timeline.push(Presentation { lead: None, ..block(base + delay / 2, 480., 480., Duration::ZERO) });
    timeline.push(block(now, 960., 480., Duration::ZERO));
    // A positively offset destination must wait for the recovered block to become audible.
    let (audible, wake) = timeline.read(now, true, 480);
    assert!(audible.is_none());
    assert_eq!(wake, Some(now + Duration::from_millis(10)));
    drop(timeline);
    port.poll("desk", now, &song, &view, &stats, &mut vec![]);
    assert_eq!(port.link.unwrap().messages, [(now, vec![0xf8])]);
}
