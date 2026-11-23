use super::*;
use crate::mtc_input::{Reader, ChaseEvent};
use soundcraft_time::SampleRate;
const RATES: [FrameRate; 6] =
    [FrameRate::Fps23_976, FrameRate::Fps24, FrameRate::Fps25, FrameRate::Fps29_97, FrameRate::Fps29_97Drop, FrameRate::Fps30];
fn stamp(piece: i64, rate: FrameRate) -> i64 {
    let (n, d) = rate.rational();
    (piece as f64 * 1e6 * d as f64 / (4. * n as f64)).round() as i64
}
fn decode_group(r: &mut Reader, frame: i64, first_piece: i64, rate: FrameRate) -> Option<ChaseEvent> {
    let group = quarters(frame, rate);
    for (i, m) in group.iter().enumerate() {
        let t = stamp(first_piece + i as i64, rate);
        r.receive(m, t, t);
    }
    r.take(stamp(first_piece + 7, rate))
}

#[test]
fn scenario_c1_c8_ten_minutes_six_rates() {
    let mut total_differences = 0;
    for rate in RATES {
        let mut r = Reader::default();
        r.options.rate = rate;
        r.source = Some(0);
        let mut stationary = Reader::default();
        let mut max = 0;
        let mut groups = 0;
        let mut frames = 0;
        let mut mismatches = 0;
        let mut wrong = [0usize; 4];
        let mut worst = 0u64;
        let mut first = None;
        let total = 600 * rate.rational().0 as i64 / rate.rational().1 as i64;
        for frame in 0..total {
            let ff = locate(frame, rate);
            let t = stamp(frame * 4, rate);
            stationary.receive(&ff, t, t);
            let Some(ChaseEvent::Locate(pos)) = stationary.take(t) else { panic!("invalid literal frame {frame} {rate:?}") };
            for (i, hz) in [44100, 48000, 96000, 192000].into_iter().enumerate() {
                let sr = SampleRate::new(hz).unwrap();
                let expected = rate.samples_at_frame(frame, sr);
                let actual = pos.session_sample(rate, sr, 0, 0);
                if actual != expected {
                    wrong[i] += 1;
                    worst = worst.max(actual.abs_diff(expected));
                    first.get_or_insert((hz, frame, actual, expected));
                }
            }
            frames += 1;
            if frame % 2 != 0 {
                continue;
            }
            let ev = decode_group(&mut r, frame, frame * 4, rate);
            if frame > 0 {
                let Some(ChaseEvent::Roll(p, _)) = ev else { panic!("no lock {rate:?} frame {frame}") };
                for hz in [44100, 48000, 96000, 192000] {
                    let sr = SampleRate::new(hz).unwrap();
                    let expected = ((frame as f64 + 1.75) * rate.samples_per_frame(sr)).round() as i64;
                    max = max.max(p.in_session_rate(rate).samples(sr).abs_diff(expected));
                }
                groups += 1;
                mismatches += usize::from(r.incoming_status().1.is_some());
            }
        }
        eprintln!(
            "C-1/C-8 {rate:?} full_frames={frames} whole_mismatches_by_sample_rate={wrong:?} worst_whole_samples={worst} first={first:?} rolling_groups={groups} max_quarter_error_samples={max} rate_warnings={mismatches}"
        );
        total_differences += wrong.iter().sum::<usize>();
        assert_eq!(mismatches, 0);
        assert!(max <= 1);
        r.options.rate = if rate == FrameRate::Fps25 { FrameRate::Fps30 } else { FrameRate::Fps25 };
        assert!(r.incoming_status().1.is_some());
    }
    assert_eq!(total_differences, 0, "MTC locates must agree with Session Setup at whole frames");
}


