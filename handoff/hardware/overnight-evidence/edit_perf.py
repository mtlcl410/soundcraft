from pathlib import Path
import sys
a = Path(__file__).resolve().parent
w = Path(sys.argv[1])
src = w / "crates/playback/src"
def replace(p, old, new):
    s = p.read_text(encoding="utf-8")
    assert s.count(old)==1,(p,old)
    p.write_bytes(s.replace(old,new).encode())
p=src/"sync_output.rs"
replace(p, "        self.max.fetch_max(us, Relaxed);", """        if us > self.max.load(Relaxed) {
            self.max.fetch_max(us, Relaxed);
        }""")
replace(p, """                stats.catch_up_sends.fetch_add(r.encoder.take_catchups(), Relaxed);
                stats.stale_dropped.fetch_add(r.encoder.take_stale_dropped(), Relaxed);""","""                let catchups = r.encoder.take_catchups();
                if catchups != 0 {
                    stats.catch_up_sends.fetch_add(catchups, Relaxed);
                }
                let stale = r.encoder.take_stale_dropped();
                if stale != 0 {
                    stats.stale_dropped.fetch_add(stale, Relaxed);
                }""")
p=src/"sync_clock.rs"
replace(p, "            self.metrics.max_gap_us.fetch_max(gap.as_micros() as u64, Relaxed);","""            let gap_us = gap.as_micros() as u64;
            if gap_us > self.metrics.max_gap_us.load(Relaxed) {
                self.metrics.max_gap_us.fetch_max(gap_us, Relaxed);
            }""")
p=src/"mtc_input.rs"
start=p.read_text(encoding="utf-8").index("        if self.jitter_count > 0 {")
stop=p.read_text(encoding="utf-8").index("        stats\n",start)
replace(p,p.read_text(encoding="utf-8")[start:stop],"""        stats.input_jitter_p95_us = percentile95(&self.jitter[..self.jitter_count]);
        stats.arrival_delay_p95_us = percentile95(&self.arrival_delays[..self.arrival_count]);
""")
pos=p.read_text(encoding="utf-8").index("impl Reader {")
replace(p,"impl Reader {","""// With at most 32 observations, the nearest-rank 95th percentile is either
// the largest value or the second largest (ties count as separate samples).
fn percentile95(samples: &[u32]) -> u32 {
    debug_assert!(samples.len() <= 32);
    if samples.len() < 20 {
        return samples.iter().copied().max().unwrap_or(0);
    }
    let mut largest = 0;
    let mut second = 0;
    for &value in samples {
        second = second.max(largest.min(value));
        largest = largest.max(value);
    }
    second
}

impl Reader {""")
p=src/"sync_input.rs"
replace(p,"    jitter: f64,","    jitter: f64,\n    tempo_ramp: std::sync::OnceLock<bool>,")
replace(p,"intercept: 0., jitter: 0. }","intercept: 0., jitter: 0., tempo_ramp: Default::default() }")
replace(p,"        self.len = 0;","        self.tempo_ramp.take();\n        self.len = 0;")
replace(p,"        self.points[self.cursor] = (pulse, at_us);","""        if N >= 24 {
            self.tempo_ramp.take();
        }
        self.points[self.cursor] = (pulse, at_us);""")
replace(p,"        let Some((last, stamp)) = self.last else { return false };","""        // UI snapshots and audio render lookahead can read the same fit several
        // times between wire pulses. Its curvature changes only on push or clear.
        *self.tempo_ramp.get_or_init(|| self.compute_tempo_ramp())
    }

    fn compute_tempo_ramp(&self) -> bool {
        let Some((last, stamp)) = self.last else { return false };""")
