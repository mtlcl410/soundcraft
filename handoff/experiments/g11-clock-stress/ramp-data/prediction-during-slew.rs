#[test]
fn stable_device_prediction_waits_for_a_continuous_tempo_ramp_to_end() {
    let mut reader = Follower::default();
    let mut stamp = 0;
    feed(&mut reader, 0xfa, stamp);
    for _ in 0..192 {
        stamp += 20_000;
        feed(&mut reader, 0xf8, stamp);
    }
    assert!(reader.render_prediction().is_some());
    // Two microseconds per pulse is well inside short-term regularity tolerance,
    // yet the sustained slowdown is measurable across the long fit.
    for i in 1..=192 {
        stamp += 20_000 + 2 * i;
        feed(&mut reader, 0xf8, stamp);
    }
    let snapshot = reader.snapshot(stamp);
    assert!(snapshot.tempo_ramp && !snapshot.recovering_tempo_step);
    assert!(reader.short.regular_intervals(reader.steady.period_us().unwrap()));
    assert!(reader.render_prediction().is_none());
    for _ in 0..192 {
        stamp += 20_384;
        feed(&mut reader, 0xf8, stamp);
    }
    assert!(reader.render_prediction().is_some());
}
