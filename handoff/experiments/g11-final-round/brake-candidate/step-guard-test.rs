#[test]
fn a_single_twenty_percent_interval_step_does_not_become_a_continuous_brake() {
    let mut f = Follower::default();
    let mut seed = 42_u64;
    let mut ideal = 0.0_f64;
    f.receive(&[0xfa], 0);
    for pulse in 0..590 {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        let noise = if pulse == 0 { 0 } else { ((seed >> 32) % 2001) as i64 - 1000 };
        let arrival = ideal.round() as i64 + noise;
        f.receive(&[0xf8], arrival);
        assert!(!f.snapshot(arrival).braking, "an abrupt interval step entered brake tracking at pulse {pulse}");
        ideal += 2_500_000. / if pulse < 396 { 120. } else { 100. };
    }
}
