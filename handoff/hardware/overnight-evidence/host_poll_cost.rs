
// Local benchmark fixture. Compile the identical function on both revisions.
#[cfg(test)]
#[test]
#[ignore]
fn acceptance_poll_cost_one_process() {
    let feed = MidiFeed::default();
    feed.set_clock(0);
    feed.set_clock_follow(Some(0), true, 0, false);
    feed.receive(0, &[0xfa]);
    for pulse in 0..32 {
        feed.set_clock(pulse * 20_833);
        feed.receive(0, &[0xf8]);
    }
    feed.set_clock(31 * 20_833 + 1);
    let mut actions = Vec::new();
    feed.clock_follow_status(&mut actions);
    for n in 0..2 {
        let t = std::time::Instant::now();
        for _ in 0..500_000 {
            std::hint::black_box(feed.clock_follow_status(&mut actions));
        }
        if n == 1 {
            println!("SC_POLL_NS {:.3}", t.elapsed().as_secs_f64() * 1e9 / 500_000.);
        }
    }
}
