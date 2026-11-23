#[test]
fn a_stop_cancels_clock_repayment_and_a_new_pass_starts_normally() {
    let base = Instant::now();
    let view = View::default();
    let song = Session::new("stop during repayment", soundcraft_time::SampleRate::HZ_48000);
    let stats = Stats::default();
    let mut port = active_port(0, true);
    let mut pending = Vec::new();
    let mut messages = Vec::new();
    for ms in 0..=410 {
        let now = base + Duration::from_millis(ms);
        if ms % 10 == 0 {
            let mut b = block(now, ms as f64 * 48., 480., Duration::ZERO);
            b.lead = (!(100..200).contains(&ms)).then_some(Duration::ZERO);
            if ms >= 300 {
                b.playing = ms >= 400;
                b.pass = if b.playing { 3 } else { 2 };
                b.sample = if b.playing { (ms - 400) as f64 * 48. } else { 14_400. };
                b.limit = b.sample + 480.;
            }
            view.lock().unwrap().push(b);
        }
        port.poll("desk", now, &song, &view, &stats, &mut pending);
        for (_, msg) in port.link.as_mut().unwrap().messages.drain(..) {
            if ms >= 300 { messages.push((ms, msg)); }
        }
    }
    assert_eq!(messages, [(300, vec![STOP]), (400, vec![START]), (400, vec![CLOCK])]);
}
