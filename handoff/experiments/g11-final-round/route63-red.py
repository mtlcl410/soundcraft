from pathlib import Path
import sys
f=Path(sys.argv[1])/'crates/playback/src/mtc_input.rs'
s=f.read_text(encoding='utf8')
needle='    #[test]\n    fn selected_feed_separates'
tests="""    #[test]
    fn framing_selected_port_accepts_interleaved_realtime_and_split_quarter_frames() {
        let feed = MidiFeed::default();
        feed.set_mtc_source(Some(1));
        feed.set_clock(0);
        for status in [0xf8, 0xfa, 0xfc] {
            let locate = [0xf0, 0x7f, 0x7f, 1, 1, status, 0x61, 0, 0, 0, 0xf7];
            feed.receive(1, &locate);
            assert!(matches!(feed.take_mtc(), Some(ChaseEvent::Locate(p)) if p.label() == "01:00:00:00"), "real-time status {status:02x}");
        }
        // Each real-time event is independent of the adjacent quarter-frame data.
        cycle(0, |b| feed.receive(1, &[b[0], 0xf8, b[1]]));
        cycle(2, |b| {
            feed.receive(1, &[b[0]]);
            feed.receive(1, &[0xf8]);
            feed.receive(2, &[b[1] ^ 1]);
            feed.receive(1, &[b[1]]);
        });
        assert!(matches!(feed.take_mtc(), Some(ChaseEvent::Roll(p, _)) if p.rate == FrameRate::Fps25));
        assert_eq!(feed.activity().0, 0);
    }

    #[test]
    fn framing_ignores_incomplete_and_oversized_timecode_then_accepts_fresh_locate() {
        let mut reader = Reader::default();
        for status in 0xf8..=0xff {
            reader.read(&[0xf0, 0x7f, 0x7f, 1, 1, status], 0);
            for _ in 0..32 {
                reader.read(&[0, status, 0], 0);
            }
            reader.read(&[0xf7], 0);
            assert!(reader.located_start.is_none());
        }
        reader.read(&[0xf0, 0x7f, 0x7f, 1, 1, 0xf8], 0);
        reader.read(&[0x60, 0, 1, 0, 0xf7], 0);
        assert!(matches!(reader.take(0), Some(ChaseEvent::Locate(p)) if p.label() == "00:00:01:00"));
    }

    #[cfg(any(target_os = "windows", target_os = "macos", target_os = "linux"))]
    #[test]
    fn framing_generator_and_chase_keep_midnight_session_samples_continuous() {
        let sr = SampleRate::new(48_000).unwrap();
        for (rate, day) in [(FrameRate::Fps30, 2_592_000), (FrameRate::Fps29_97Drop, 2_589_408)] {
            let mut reader = Reader::default();
            let session_start = rate.samples_at_frame(day / 24, sr);
            let mut last = None;
            for (n, frame) in [day - 4, day - 2, day, day + 2].into_iter().enumerate() {
                for (i, bytes) in crate::mtc::quarters(frame, rate).into_iter().enumerate() {
                    reader.read(&bytes, ((n * 8 + i) as f64 * Position { quarter: 0, rate }.frame_us() / 4.).round() as i64);
                }
                if n == 0 {continue;}
                let (position, _) = reader.rolling.expect("two contiguous forward groups lock");
                let sample = position.session_sample(rate, sr, session_start, 0);
                if let Some(previous) = last {
                    assert!(sample > previous && (sample - previous).abs_diff(rate.samples_at_frame(2, sr)) <= 1,
                        "{rate:?} midnight: {previous} → {sample}");
                }
                last = Some(sample);
                if frame == day {
                    assert!(reader.incoming.unwrap().label().starts_with("00:00:00"), "generator and incoming display must wrap");
                }
            }
            assert_eq!((reader.stats.locks, reader.stats.losses, reader.stats.hard_relocates, reader.seek_generation), (1, 0, 0, 0));
            reader.read(&[0xf0, 0x7f, 127, 1, 1, if rate.is_drop() {0x40} else {0x60}, 12, 0, 0, 0xf7], 300_000);
            let Some(ChaseEvent::Locate(p)) = reader.take(300_000) else {panic!("explicit locate")};
            assert!(p.samples(sr) < rate.samples_at_frame(day, sr), "unrelated full-frame locate starts a new day");
        }
    }

    #[test]
    fn framing_adjacent_full_frame_rewind_crosses_to_the_previous_day() {
        let mut reader = Reader::default();
        let locate = |reader: &mut Reader, h, m, s, f| {
            reader.read(&[0xf0,0x7f,127,1,1,0x60 | h,m,s,f,0xf7], 0);
            let Some(ChaseEvent::Locate(p)) = reader.take(0) else {panic!("full-frame locate")};
            p
        };
        let midnight = locate(&mut reader, 0,0,0,0);
        let prev = locate(&mut reader, 23,59,59,29);
        assert_eq!(prev.quarter, midnight.quarter - 4);
        assert_eq!(prev.label(), "23:59:59:29");
    }

"""
assert s.count(needle)==1
f.write_text(s.replace(needle,tests+needle),encoding='utf8')
