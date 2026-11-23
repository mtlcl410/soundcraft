#[cfg(test)]
mod stop_boundary_tests {
    use super::*;
    use std::sync::{Arc,Mutex};
    use crate::midi::MidiFeed;
    use super::super::{Output, SyncPort};
    use std::time::{Instant,Duration};

    struct Wire(Arc<Mutex<Vec<Vec<u8>>>>);
    impl SyncPort for Wire {
        fn send_at(&mut self, _:Instant, bytes:&[u8])->Result<Instant,String>{
            self.0.lock().unwrap().push(bytes.to_vec());
            Ok(Instant::now())
        }
    }

    fn check(start:i64, coast:bool, outgoing_pass:u64, final_clocks:usize, expect:usize) {
        let mut output=Output::default();
        let feed=Arc::new(MidiFeed::default());
        output.attach_mtc_feed(&feed);
        feed.set_clock_follow(Some(0),true,0,false);
        let spp=[0xf2,(start/6) as u8,0];
        let launch=if start==0 {0xfa} else {0xfb};
        feed.receive_at(0,&spp,0);
        feed.receive_at(0,&[launch],0);
        feed.receive_at(0,&[0xf8],0);
        feed.clock_audio_pass.store(42,std::sync::atomic::Ordering::Release);
        feed.receive_at(0,&[0xf8],20_833);
        feed.receive_at(0,&[0xfc],if coast {900_000} else {22_000});

        let sent=Arc::new(Mutex::new(Vec::new()));
        let mut port=PortIo::new(Wire(sent.clone()),output.stats.clone()).unwrap();
        let now=Instant::now();
        port.submit(now,&spp,false,&output.stats).unwrap();
        port.submit(now,&[launch],false,&output.stats).unwrap();
        for _ in 0..final_clocks {
            port.submit_beat(now,outgoing_pass,&output.stats).unwrap();
        }
        port.submit(now,&[0xfc],true,&output.stats).unwrap();
        port.flush();
        let mut cleanup=VecDeque::new();
        let end=Instant::now()+Duration::from_secs(2);
        while !port.ready(&mut cleanup).unwrap() {
            assert!(Instant::now()<end);
            std::thread::yield_now();
        }
        let sent=sent.lock().unwrap();
        assert_eq!(sent.iter().filter(|msg| msg.as_slice()==[0xf8]).count(),expect);
        assert_eq!(sent.last().unwrap().as_slice(),[0xfc]);
    }
    #[test]
    fn explicit_external_stop_keeps_the_owed_clock_and_rejects_only_surplus() {
        check(0,false,42,3,2);
    }
    #[test]
    fn nonzero_continue_stop_uses_absolute_pulses_and_only_its_audio_pass() {
        check(96,false,42,3,2);
        check(96,false,43,3,3);
    }
    #[test]
    fn stop_after_loss_does_not_bound_coasting_by_the_old_wire_count() {
        check(0,true,42,3,3);
    }
}

