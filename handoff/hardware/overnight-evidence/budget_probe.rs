
#[test]
#[ignore = "opt-in timing profile; wall-clock quantiles depend on host load"]
fn bounded_prefix_cost_when_a_dry_stereo_guide_fills_the_scan_budget() {
    use std::hint::black_box;
    use std::time::Instant;
    let s = guide();
    for (label, from, to) in [("2x16384 zeros", 13000, 29384), ("2x16385 exceeds cap",13000,29385), ("nonzero second channel",0,12001)] {
        let mut elapsed=Vec::with_capacity(10000);
        for _ in 0..10000 {
            let t=Instant::now();
            black_box(silent_pcm_prefix(black_box(&s),from,to));
            elapsed.push(t.elapsed().as_nanos());
        }
        elapsed.sort_unstable();
        println!("prefix {label}: {} calls; p50 {} ns p95 {} ns p99 {} ns max {} ns",elapsed.len(),elapsed[4999],elapsed[9499],elapsed[9899],elapsed[9999]);
    }
}

