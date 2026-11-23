#[test]
fn recovered_clock_repays_missing_ticks_evenly_within_one_beat() {
    let base = Instant::now();
    let capture = |gap: std::ops::Range<u64>| {
        let view = View::default();
        let song = Session::new("clock recovery", soundcraft_time::SampleRate::HZ_48000);
        let mut port = active_port(0, true);
        let stats = Stats::default();
        let mut pending = Vec::new();
        let mut ticks = Vec::new();
        let mut transport = Vec::new();
        for ms in 0..=1000 {
            let now = base + Duration::from_millis(ms);
            if ms % 10 == 0 {
                let lead = (!gap.contains(&ms)).then_some(Duration::ZERO);
                view.lock().unwrap().push(Presentation { lead, ..block(now, ms as f64 * 48., 480., Duration::ZERO) });
            }
            port.poll("desk", now, &song, &view, &stats, &mut pending);
            for (due, msg) in port.link.as_mut().unwrap().messages.drain(..) {
                if msg == [CLOCK] {
                    ticks.push((ms, due.duration_since(base).as_secs_f64() * 1000.));
                } else {
                    transport.push((ms, msg));
                }
            }
        }
        (ticks, transport)
    };
    let (reference, reference_transport) = capture(0..0);
    for gap in [100..200, 50..250] {
        let (ticks, transport) = capture(gap.clone());
        let beat_end = gap.end + 500;
        let recovered: Vec<_> = ticks.iter().copied().filter(|(ms, _)| (gap.end..beat_end).contains(ms)).collect();
        let intervals: Vec<_> = recovered.windows(2).map(|p| p[1].0 - p[0].0).collect();
        eprintln!("gap={gap:?} first={:?} intervals_ms={intervals:?} count={}/{} recovery_ticks={}", recovered.first(), ticks.len(), reference.len(),recovered.len());
        assert_eq!(transport, reference_transport);
        assert!(ticks.iter().all(|(ms,_)| !gap.contains(ms)));
        assert_eq!(ticks.len(), reference.len());
        assert_eq!(ticks.iter().filter(|(ms,_)| *ms < beat_end).count(), reference.iter().filter(|(ms,_)| *ms < beat_end).count());
        let first_live = reference.iter().find(|(ms,_)| *ms >= gap.end).unwrap();
        assert_eq!(recovered[0], *first_live);
        assert!(recovered.iter().all(|(ms,due)| (0.0..=1.001).contains(&(*ms as f64 - due))));
        assert!(intervals.iter().min().unwrap() > &1);
        assert!(intervals.iter().max().unwrap() - intervals.iter().min().unwrap() <= 1);
        let after = |rows: &[(u64,f64)]| rows.iter().copied().filter(|(ms,_)| *ms >= beat_end).collect::<Vec<_>>();
        assert_eq!(after(&ticks), after(&reference));
    }
}
