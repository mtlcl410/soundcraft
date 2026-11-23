from pathlib import Path
import sys
src=Path(sys.argv[1])/'crates/playback/src'
def edit(name, old, new):
    p=src/name;s=p.read_text(encoding='utf-8');assert s.count(old)==1;p.write_bytes(s.replace(old,new).encode())
edit('mtc_input.rs','fn percentile95(samples: &[u32]) -> u32 {\n    debug_assert!(samples.len() <= 32);','fn percentile95(window: &[u32; 32], count: usize) -> u32 {\n    let samples = &window[..count];')
edit('mtc_input.rs','percentile95(&self.jitter[..self.jitter_count])','percentile95(&self.jitter, self.jitter_count)')
edit('mtc_input.rs','percentile95(&self.arrival_delays[..self.arrival_count])','percentile95(&self.arrival_delays, self.arrival_count)')
edit('mtc_input.rs','    fn read_with_jitter(','''    #[test]
    fn diagnostic_percentiles_match_sorted_prefixes_with_ties_and_outliers() {
        for seed in 0..64u32 {
            let values = std::array::from_fn(|i| match (i as u32 + seed) % 5 {
                0 => u32::MAX,
                1 | 2 => 0,
                _ => (i as u32 * 7919 + seed * 613) % 1009,
            });
            for count in 0..=values.len() {
                let mut expected = values[..count].to_vec();
                expected.sort_unstable();
                assert_eq!(percentile95(&values, count), expected.get((count * 95).div_ceil(100).wrapping_sub(1)).copied().unwrap_or(0));
            }
        }
    }

    fn read_with_jitter(''')
edit('sync_input.rs','    #[test]\n    fn eight_percent_bpm_steps', '''    #[test]
    fn repeated_ramp_queries_follow_each_new_pulse_and_transport_reset() {
        let mut fit = PulseFit::<192>::default();
        let mut t = 0;
        let mut saw_ramp = false;
        for pulse in 0..1800 {
            t += if (300..800).contains(&pulse) { 15000 + (pulse - 300) * 10 } else { 20000 };
            fit.push(pulse, t + pulse % 3);
            let value = fit.is_tempo_ramp();
            saw_ramp |= value;
            for _ in 0..8 {
                assert_eq!(value, fit.is_tempo_ramp());
            }
            if pulse >= 23 {
                assert_eq!(value, fit.compute_tempo_ramp());
            }
            if pulse > 1100 {
                assert!(!value);
            }
        }
        assert!(saw_ramp);
        fit.push(0, 1);
        assert!(!fit.is_tempo_ramp());
        fit.clear();
        assert!(!fit.is_tempo_ramp());
    }

    #[test]
    fn eight_percent_bpm_steps''')
p=src/'sync_output/tests.rs';s=p.read_text(encoding='utf-8');p.write_bytes((s+'''
#[test]
fn concurrent_delivery_stats_keep_every_event_and_the_largest_delay() {
    let stats = Stats::default();
    let at = Instant::now();
    std::thread::scope(|threads| {
        for writer in 0..4 {
            let stats = &stats;
            threads.spawn(move || {
                for i in 0..1000 {
                    stats.record(at, at + Duration::from_micros((999 - i) * 4 + writer));
                }
            });
        }
    });
    assert_eq!(stats.sent.load(Relaxed), 4000);
    assert_eq!(stats.max.load(Relaxed), 3999);
    assert_eq!(stats.buckets.iter().map(|value| value.load(Relaxed)).sum::<u64>(), 4000);
}
''').encode())
