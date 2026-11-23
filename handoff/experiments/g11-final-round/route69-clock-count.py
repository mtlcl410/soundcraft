from pathlib import Path
import sys
p=Path(sys.argv[1])/'crates/playback/src/mtc_input.rs'
s=p.read_text(encoding='utf8')
needle='    #[test]\n    fn framing_selected_port_'
test="""    #[test]
    fn clock_and_timecode_share_interleaved_realtime_without_double_counting() {
        let feed = MidiFeed::default();
        feed.set_mtc_source(Some(1));
        feed.set_clock_follow(Some(1), false, 0, false);
        feed.set_clock(0);
        feed.receive(1, &[0xfa, 0xf8]);
        assert_eq!(feed.clock_follow_status(&mut Vec::new()).pulse, 0);
        feed.set_clock(20_000);
        feed.receive(1, &[0xf0, 0x7f, 0x7f, 1, 1, 0xf8, 0x61, 0, 0, 0, 0xf7]);
        assert_eq!(feed.clock_follow_status(&mut Vec::new()).pulse, 1);
        assert!(matches!(feed.take_mtc(), Some(ChaseEvent::Locate(p)) if p.label() == "01:00:00:00"));
        feed.set_clock(40_000);
        feed.receive(1, &[0xf1, 0xf8, 0]);
        assert_eq!(feed.clock_follow_status(&mut Vec::new()).pulse, 2);
    }

"""
assert s.count(needle)==1
p.write_text(s.replace(needle,test+needle),encoding='utf8')
