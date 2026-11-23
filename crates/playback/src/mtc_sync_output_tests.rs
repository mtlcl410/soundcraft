use super::*;
use crate::sync_clock::Presentation;
use std::sync::atomic::AtomicUsize;
use std::sync::mpsc::channel;
type Handoff = (Instant, Instant, Vec<u8>);
struct Capture(Arc<Mutex<Vec<Handoff>>>);
impl SyncPort for Capture {
    fn send_at(&mut self, at: Instant, bytes: &[u8]) -> Result<Instant, String> {
        let actual = Instant::now();
        self.0.lock().unwrap().push((at, actual, bytes.to_vec()));
        Ok(actual)
    }
}

#[test]
fn an_mtc_route_is_cached_only_after_the_worker_accepts_it() {
    let mut output = Output::default();
    let port = Some(("model".to_owned(), 240));
    assert!(!output.encoder(port.clone(), true, Box::<crate::mtc::Encoder>::default()));
    assert_eq!(output.additional, None, "no session or worker accepted this route");

    let (tx, rx) = channel();
    let worker = std::thread::spawn(|| {});
    output.worker = Some((WorkerSender { tx, worker: worker.thread().clone() }, worker));
    assert!(output.encoder(port.clone(), true, Box::<crate::mtc::Encoder>::default()));
    assert!(matches!(rx.try_recv(), Ok(Update::Encoder(name, true, _)) if name == port));
    assert_eq!(output.additional, Some(("model".to_owned(), 240, true)));
}

#[test]
fn a_burst_of_external_locates_queues_one_transport_refresh() {
    let output = Output::default();
    let wake = output.transport_waker();
    let (tx, rx) = channel();
    *output.wake_tx.lock().unwrap() = Some(WorkerSender { tx, worker: std::thread::current() });
    use crate::mtc_input::{ChaseEvent, Reader};
    let mut reader = Reader::default();
    reader.receive(&[0xf0, 0x7f, 0x7f, 1, 1, 0, 0, 1, 0, 0xf7], 0, 0);
    let locate = reader.pending.unwrap();
    let ChaseEvent::Locate(position) = locate else {
        panic!("expected full frame");
    };
    let stopped = super::tests::block(Instant::now(), 0., 0., Duration::ZERO);
    output.view.lock().unwrap().push(Presentation { pass: 5, playing: false, ..stopped });
    wake(ChaseEvent::Stop);
    assert!(rx.try_recv().is_err());
    for _ in 0..100 {
        wake(locate);
    }
    output.view.lock().unwrap().push(Presentation { pass: 6, playing: true, ..stopped });
    let Ok(Update::TransportWake(pending, Some((5, false)))) = rx.try_recv() else {
        panic!("expected the transport state before the callback consumed the locate");
    };
    assert!(rx.try_recv().is_err());
    pending.store(false, Relaxed);
    wake(ChaseEvent::Roll(position, 0));
    assert!(rx.try_recv().is_err());
    wake(ChaseEvent::Stop);
    assert!(matches!(rx.try_recv(), Ok(Update::TransportWake(_, Some((6, true))))));
}

#[test]
fn both_encoders_use_one_connection_and_the_same_offset() {
    let now = Instant::now();
    let lead = Duration::from_millis(30);
    let due = now + Duration::from_millis(25);
    let mut map = BTreeMap::new();
    set_route(&mut map, 0, "device".to_owned(), Route { map: None, offset: -240, compensate: true, encoder: Box::<Cursor>::default() });
    set_route(&mut map, 1, "device".to_owned(), Route { map: None, offset: -240, compensate: true, encoder: Box::<crate::mtc::Encoder>::default() });
    assert_eq!(map.len(), 1);
    let messages = Arc::default();
    let p = map.get_mut("device").unwrap();
    p.link = Some(Capture(Arc::clone(&messages)));
    let v = View::default();
    v.lock().unwrap().push(Presentation {
        generation: 0,
        sample_rate: soundcraft_time::SampleRate::HZ_48000,
        system_delay_samples: 0,
        pass: 1,
        origin: 0,
        playing: true,
        sample: 0.,
        limit: 4800.,
        heard_at: now + lead,
        samples_per_second: 48_000.,
        looped: None,
        end: None,
        lead: Some(lead),
    });
    let mut s = Session::new("coexisting encoders", soundcraft_time::SampleRate::HZ_48000);
    s.frame_rate = soundcraft_time::FrameRate::Fps30;
    s.timecode_start = 0;
    for i in 0..100 {
        p.poll("device", due + Duration::from_millis(i), &s, &v, &Stats::default(), &mut Vec::new());
    }
    let data = messages.lock().unwrap();
    assert!(data.windows(2).all(|r| r[0].0 <= r[1].0));
    assert!(data.iter().any(|(t, _, b)| *t == due && b == &[0xf8]));
    assert!(data.iter().any(|(t, _, b)| *t == due && b == &[0xf1, 0]));
    assert_eq!(data.iter().filter(|(_, _, m)| m[0] == 0xf1).count(), 12);
}

#[test]
fn generator_waits_for_observed_presentation_only_when_compensation_is_enabled() {
    let now = Instant::now();
    let mut song = Session::new("MTC output", soundcraft_time::SampleRate::HZ_48000);
    song.frame_rate = soundcraft_time::FrameRate::Fps25;
    song.timecode_start = 0;
    for compensate in [true, false] {
        let mut routes = BTreeMap::new();
        set_route(&mut routes, 1, "MTC".into(), Route { map: None, offset: 0, compensate, encoder: Box::<crate::mtc::Encoder>::default() });
        let port = routes.get_mut("MTC").unwrap();
        let capture = Arc::default();
        port.link = Some(Capture(Arc::clone(&capture)));
        let view = View::default();
        let block = super::tests::block(now, 0., 4800., Duration::ZERO);
        view.lock().unwrap().push(Presentation { lead: None, ..block });
        port.poll("MTC", now, &song, &view, &Stats::default(), &mut Vec::new());
        assert_eq!(capture.lock().unwrap().is_empty(), compensate);

        // A real zero report allows immediate delivery, even on the compensated route.
        let next = now + Duration::from_millis(10);
        view.lock().unwrap().push(Presentation { heard_at: next, sample: 480., ..block });
        port.poll("MTC", next, &song, &view, &Stats::default(), &mut Vec::new());
        assert!(capture.lock().unwrap().iter().any(|(_, _, msg)| msg[0] == 0xf1));
    }
}

#[test]
fn mtc_quarters_use_the_mixer_delay_and_report_limited_negative_advances() {
    use soundcraft_time::{FrameRate, SampleRate};
    let base = Instant::now();
    let lead = Duration::from_millis(20);
    let mut session = Session::new("generator delay", SampleRate::HZ_48000);
    session.frame_rate = FrameRate::Fps25;
    session.timecode_start = 0;
    for (offset, delay, expected_us, limited) in
        [(-4800, 0, 1000, true), (-4800, 2400, 1000, true), (0, 2400, 70000, false), (480, 2400, 80000, false)]
    {
        let cable = View::default();
        let mut routes = BTreeMap::new();
        set_route(&mut routes, 1, "MTC".into(), Route { map: None, offset, compensate: true, encoder: Box::<crate::mtc::Encoder>::default() });
        let p = routes.get_mut("MTC").unwrap();
        let packets = Arc::new(Mutex::new(Vec::new()));
        p.link = Some(Capture(packets.clone()));
        let stats = Stats::default();
        for ms in 0..=500 {
            let now = base + Duration::from_millis(ms);
            if ms % 10 == 0 {
                cable.lock().unwrap().push(Presentation {
                    generation: 0,
                    sample_rate: session.sample_rate,
                    system_delay_samples: delay,
                    pass: 1,
                    origin: 0,
                    playing: true,
                    sample: ms as f64 * 48.,
                    limit: ms as f64 * 48. + 480.,
                    heard_at: now + lead,
                    lead: Some(lead),
                    samples_per_second: 48000.,
                    looped: None,
                    end: None,
                });
            }
            p.poll("MTC", now, &session, &cable, &stats, &mut Vec::new());
        }
        let onsets: Vec<_> =
            packets.lock().unwrap().iter().filter(|(_, _, b)| b[0] == 0xf1).map(|(at, _, _)| at.duration_since(base).as_micros() as i64).collect();
        assert!(onsets.len() > 40, "{onsets:?}");
        for (index, onset) in onsets.into_iter().enumerate() {
            assert!(onset.abs_diff(expected_us + index as i64 * 10000) <= 1, "offset {offset}, delay {delay}, quarter {index}, onset {onset}");
        }
        let mut output = Output::default();
        output.additional = Some(("MTC".into(), offset, true));
        crate::sync_clock::Publisher::new(output.view.clone(), output.metrics.clone())
            .observe(crate::sync_clock::DeviceTiming::new(base, Some(lead), 0), 0.005);
        output.metrics.system_delay_samples.store(delay as u64, Relaxed);
        let status = output.status();
        assert_eq!(status.ports["MTC"].mtc_total_us, Some(expected_us));
        assert_eq!(status.ports["MTC"].advance_limited, limited);
    }
}

#[test]
fn mtc_rate_and_start_change_at_the_first_rendered_block_of_the_new_generation() {
    use soundcraft_time::{FrameRate, SampleRate};
    let base = Instant::now();
    let mut first = Session::new("old", SampleRate::HZ_48000);
    first.timecode_start = 0;
    first.frame_rate = FrameRate::Fps30;
    let first = Arc::new(first);
    let mut edited = (*first).clone();
    edited.timecode_start = 48000 * 3600;
    edited.frame_rate = FrameRate::Fps25;
    let edited = Arc::new(edited);
    let view = View::default();
    view.lock().unwrap().register(SessionRevision { generation: 1, doc: first, remap: true }, true);
    let mut routes = BTreeMap::new();
    set_route(&mut routes, 1, "MTC".into(), Route { map: None, offset: 0, compensate: false, encoder: Box::<crate::mtc::Encoder>::default() });
    let cable = routes.get_mut("MTC").unwrap();
    let packets = Arc::new(Mutex::new(Vec::new()));
    cable.link = Some(Capture(packets.clone()));
    let stats = Stats::default();
    for ms in 0..220u64 {
        let now = base + Duration::from_millis(ms);
        if ms == 50 {
            view.lock().unwrap().register(SessionRevision { generation: 2, doc: edited.clone(), remap: true }, true);
        }
        if ms % 10 == 0 {
            view.lock().unwrap().push(Presentation {
                generation: if ms >= 150 { 2 } else { 1 },
                sample_rate: SampleRate::HZ_48000,
                system_delay_samples: 0,
                pass: 1,
                origin: 0,
                playing: true,
                sample: ms as f64 * 48.,
                limit: ms as f64 * 48. + 480.,
                heard_at: now,
                lead: Some(Duration::ZERO),
                samples_per_second: 48000.,
                looped: None,
                end: None,
            });
        }
        cable.poll("MTC", now, &edited, &view, &stats, &mut Vec::new());
    }
    let locates: Vec<_> =
        packets.lock().unwrap().iter().filter(|(_, _, b)| b[0] == 0xf0).map(|(at, _, b)| (at.duration_since(base).as_millis(), b[5])).collect();
    assert_eq!(locates, vec![(0, 0x60), (150, 0x21)]);
}

/// Route the real encoder through the worker's SyncPort boundary into a second
/// transport. Each device queues 30 ms of audio after its callback. Compare the
/// sound heard at the same instant rather than either device's render cursor.
#[test]
fn generator_and_slave_agree_on_heard_time_after_acquisition() {
    use crate::midi::MidiFeed;
    use crate::sync_clock::{DeviceTiming, Publisher};
    use crate::{AudioState, Cmd, Shared};
    use soundcraft_time::{FrameRate, SampleRate};

    struct Cable {
        input: Arc<MidiFeed>,
        epoch: Instant,
    }
    impl SyncPort for Cable {
        fn send_at(&mut self, at: Instant, bytes: &[u8]) -> Result<Instant, String> {
            self.input.set_clock(at.duration_since(self.epoch).as_micros() as i64);
            self.input.receive(0, bytes);
            Ok(at)
        }
    }

    let mut sess = Session::new("MTC loopback", SampleRate::HZ_48000);
    sess.frame_rate = FrameRate::Fps25;
    sess.timecode_start = 0;
    let session = Arc::new(sess);
    let input = Arc::new(MidiFeed::default());
    input.set_mtc_options(session.frame_rate, 8, false, 0);
    input.set_mtc_source(Some(0));

    let now = Instant::now();
    let lead = Duration::from_millis(30);
    let mut routes = BTreeMap::new();
    set_route(&mut routes, 1, "cable".into(), Route { map: None, offset: 0, compensate: true, encoder: Box::<crate::mtc::Encoder>::default() });
    let port = routes.get_mut("cable").unwrap();
    port.link = Some(Cable { input: input.clone(), epoch: now });
    let master = View::default();
    let slave = View::default();
    let shared = Arc::new(Shared { position: 0.into(), playing: false.into(), speed: 1000.into(), meters: Default::default() });
    let (tx, rx) = channel();
    let mut audio = AudioState::new(rx, shared, session.clone(), 48_000., channel().0);
    tx.send(Cmd::Midi(input.clone())).unwrap();
    tx.send(Cmd::Clock(Some(Publisher::new(slave.clone(), Default::default())))).unwrap();
    let stats = Stats::default();
    let mut pending = Vec::new();
    let mut worst = 0.;
    for i in 0..=600 {
        let sample = (i * 240) as f64;
        let clock = now + Duration::from_millis(i as u64 * 5);
        master.lock().unwrap().push(Presentation {
            generation: 0,
            sample_rate: soundcraft_time::SampleRate::HZ_48000,
            system_delay_samples: 0,
            pass: 1,
            origin: 0,
            playing: true,
            sample,
            limit: sample + 240.,
            heard_at: clock + lead,
            samples_per_second: 48_000.,
            looped: None,
            end: None,
            lead: Some(lead),
        });
        port.poll("cable", clock, &session, &master, &stats, &mut pending);
        input.set_clock(i as i64 * 5000);
        audio.device_timing = Some(DeviceTiming::new(clock, Some(lead), 0));
        audio.fill(&mut [0.; 480], 2);
        if i >= 300 {
            let audible = |v: &View| v.lock().unwrap().read(clock, true, 0).0.unwrap().sample_heard_at(clock);
            worst = f64::max(worst, (audible(&master) - audible(&slave)).abs());
        }
    }
    assert_eq!(input.mtc_diagnostics().locks, 1);
    assert_eq!(input.mtc_diagnostics().hard_relocates, 1);
    assert!(worst <= 48., "master/slave heard position varies by {worst} samples at 48 kHz");
}
/// Real OS scheduling observations for the two encoders sharing a mock connection.
/// No wall-clock upper bound is a correctness gate.
#[test]
#[ignore]
fn measure_native_worker_quarter_frame_spacing() {
    for fps in [24, 30] {
        let mut sess = Session::new("quarter-frame spacing", soundcraft_time::SampleRate::HZ_48000);
        sess.timecode_start = 0;
        sess.frame_rate = if fps == 24 { soundcraft_time::FrameRate::Fps24 } else { soundcraft_time::FrameRate::Fps30 };
        let samples = Arc::new(Mutex::new(Vec::new()));
        let opens = Arc::new(AtomicUsize::new(0));
        let v = View::default();
        let (tx, rx) = channel();
        let start = Instant::now() + Duration::from_millis(80);
        v.lock().unwrap().push(Presentation {
            generation: 0,
            sample_rate: soundcraft_time::SampleRate::HZ_48000,
            system_delay_samples: 0,
            pass: 1,
            origin: 0,
            playing: true,
            sample: 0.,
            limit: 240_000.,
            heard_at: start,
            samples_per_second: 48_000.,
            looped: None,
            end: None,
            lead: Some(Duration::from_millis(30)),
        });
        let captured = samples.clone();
        let times = opens.clone();
        let worker = std::thread::spawn(move || {
            drive(v, Arc::new(sess), rx, Arc::default(), Arc::default(), move |_| {
                times.fetch_add(1, Relaxed);
                Ok((Capture(captured.clone()), None))
            })
        });
        tx.send(Update::Beats(vec![("capture".into(), 0)], true)).unwrap();
        tx.send(Update::Encoder(Some(("capture".into(), 0)), true, Box::<crate::mtc::Encoder>::default())).unwrap();
        std::thread::sleep(start.saturating_duration_since(Instant::now()) + Duration::from_millis(5100));
        drop(tx);
        worker.join().unwrap();
        assert_eq!(opens.load(Relaxed), 1);
        let rows = samples.lock().unwrap();
        let q: Vec<_> = rows.iter().filter(|r| r.2[0] == 0xf1).collect();
        let ideal = 250. / f64::from(fps);
        let mut gaps: Vec<_> = q.windows(2).map(|w| (w[1].1 - w[0].1).as_secs_f64() * 1000.).collect();
        let pairs = gaps.iter().filter(|v| **v < 1.).count();
        for dt in &mut gaps {
            *dt = (*dt - ideal).abs();
        }
        let mut late: Vec<_> = q.iter().map(|r| r.1.saturating_duration_since(r.0).as_secs_f64() * 1000.).collect();
        gaps.sort_by(f64::total_cmp);
        late.sort_by(f64::total_cmp);
        assert!(!gaps.is_empty());
        println!(
            "fps={fps} qf={} pairs_lt_1ms={pairs} interval_error_p95_ms={:.3} lateness_p95_ms={:.3}",
            q.len(),
            gaps[gaps.len() * 95 / 100],
            late[late.len() * 95 / 100]
        );
    }
}

#[test]
fn scenario_a10_dual_encoder_recovers_after_midroll_invalid_timestamp() {
    let origin=Instant::now();
    let mut song=Session::new("reset",soundcraft_time::SampleRate::HZ_48000);
    song.frame_rate=soundcraft_time::FrameRate::Fps25; song.timecode_start=0;
    let mut routes=BTreeMap::new();
    set_route(&mut routes,0,"desk".into(),Route{map:None,offset:0,compensate:true,encoder:Box::<Cursor>::default()});
    set_route(&mut routes,1,"desk".into(),Route{map:None,offset:0,compensate:true,encoder:Box::<crate::mtc::Encoder>::default()});
    let port=routes.get_mut("desk").unwrap();
    let capture=Arc::default();port.link=Some(Capture(Arc::clone(&capture)));
    let view=View::default();let stats=Stats::default();
    let mut bad=0; let mut errs:[Vec<f64>;2]=Default::default(); let mut seen=[0usize;2]; let mut dispatch=[0f64;2];
    for ms in 0..401u64 {
        let now=origin+Duration::from_millis(ms);
        if ms%10==0 {
            let block=super::tests::block(now,(ms*48) as f64,480.,Duration::ZERO);
            let lead=if (100..200).contains(&ms){None}else{Some(Duration::ZERO)};
            view.lock().unwrap().push(Presentation{lead,..block});
        }
        let before=capture.lock().unwrap().len();
        port.poll("desk",now,&song,&view,&stats,&mut Vec::new());
        let rows=capture.lock().unwrap();
        for (due,_,msg) in &rows[before..] {
            let (k,interval)=match msg[0]{0xf8=>(0,60./120./24.),0xf1=>(1,0.01),_=>continue};
            if (101..200).contains(&ms){bad+=1;}
            if ms>=200 {
                if now.saturating_duration_since(*due)>Duration::from_millis(2){eprintln!("A10 late kind={k} handoff_ms={ms} tagged_ms={:.3}",due.duration_since(origin).as_secs_f64()*1e3);} seen[k]+=1;dispatch[k]=dispatch[k].max(now.saturating_duration_since(*due).as_secs_f64()*1000.);
                let s=due.duration_since(origin).as_secs_f64();errs[k].push((s-(s/interval).round()*interval).abs()*1000.);
            }
        }
    }
    let max=errs.map(|v|v.into_iter().fold(0f64,f64::max));
    eprintln!("A10 invalid_for_ms=100 packets_while_unknown={bad} after_recovery={seen:?} max_due_grid_ms={max:?} max_handoff_after_due_ms={dispatch:?}");
    assert!(seen.iter().all(|n|*n>3)&&bad==0&&max.iter().all(|e|*e<=1.)&&dispatch.iter().all(|e|*e<=1.));
}
#[test]
fn scenario_a10_d4_two_encoders_and_stream_reset() {
    use crate::sync_clock::StreamLead;
    struct ScheduledCapture {poll_time:Arc<Mutex<Instant>>, data:Arc<Mutex<Vec<Handoff>>>}
    impl SyncPort for ScheduledCapture {
        fn send_at(&mut self, at:Instant, bytes:&[u8])->Result<Instant,String> {
            let now=*self.poll_time.lock().unwrap();
            self.data.lock().unwrap().push((at,now,bytes.to_vec()));Ok(now)
        }
    }
    let base=Instant::now();
    let out=Output::default();
    let mut pubber=Publisher::new(out.view.clone(),out.metrics.clone());
    let mut hardware=StreamLead::default();
    let mut s=Session::new("pre/post",soundcraft_time::SampleRate::HZ_48000);
    s.frame_rate=soundcraft_time::FrameRate::Fps25;s.timecode_start=0;
    let mut routes=BTreeMap::new();
    set_route(&mut routes,0,"loop".into(),Route{map:None,offset:0,compensate:true,encoder:Box::<Cursor>::default()});
    set_route(&mut routes,1,"loop".into(),Route{map:None,offset:0,compensate:true,encoder:Box::<crate::mtc::Encoder>::default()});
    let port=routes.get_mut("loop").unwrap();let data=Arc::default();let poll_time=Arc::new(Mutex::new(base));
    port.link=Some(ScheduledCapture{poll_time:poll_time.clone(),data:Arc::clone(&data)});
    // Selection [1, 2] seconds, 500 ms pre-roll and 250 ms post-roll.
    let origin=24000;let end=108000;let mut waiting=0;let mut warnings=Vec::new();
    for ms in 0..=1760 {
        let now=base+Duration::from_millis(ms);
        if ms%10==0 {
            if ms==300 {hardware=StreamLead::default();}
            let valid=ms<250 || ms>=500;
            let timing=hardware.observe(now,valid.then_some(Duration::ZERO));let lead=timing.lead();
            pubber.observe(timing,0.010);
            let warning=format!("{:?}",out.timing_issue());
            if warnings.last().is_none_or(|(_,old)|old!=&warning){warnings.push((ms,warning));}
            let playing=ms<1750;
            let pos=(origin+ms as i64*48).min(end);
            let b=Presentation{generation:0,sample_rate:s.sample_rate,system_delay_samples:0,pass:if playing{1}else{2},
                origin:if playing{origin}else{end},playing,sample:pos as f64,heard_at:now,samples_per_second:48000.,
                limit:(pos+480).min(end) as f64,looped:None,end:Some(end),lead};
            pubber.publish(b);
        }
        *poll_time.lock().unwrap()=now;
        port.poll("loop",now,&s,&out.view,&out.stats,&mut Vec::new());
        waiting+=usize::from(port.waiting_for_timing);
    }
    let data=data.lock().unwrap();
    let first=data.iter().position(|(_,_,m)|m[0]==0xf0).unwrap();
    let first_q=data.iter().position(|(_,_,m)|m[0]==0xf1).unwrap();
    assert!(first<first_q);
    assert_eq!(&data[first].2[5..9],&[0x20,0,0,12]); // 500 ms, floored to frame 12.
    assert_eq!(&data.iter().find(|(_,_,m)|m[0]==0xf2).unwrap().2,&[0xf2,4,0]);
    assert!(data.iter().any(|(t,_,m)|m==&[0xfc] && t.duration_since(base)==Duration::from_millis(1750)));
    let mut offsets=[Vec::new(),Vec::new()];
    for (deadline,handoff,m) in data.iter().filter(|(t,_,_)|t.duration_since(base)>=Duration::from_millis(600)) {
        if let Some(i)=[0xf8,0xf1].iter().position(|b|*b==m[0]) {
           let us=deadline.duration_since(base).as_micros() as i64;
           let period=if i==0{1_000_000./48.}else{10000.};
           let expected=(us as f64/period).round()*period;
           offsets[i].push(handoff.duration_since(base).as_micros() as i64-expected.round() as i64);
        }
    }
    let recovery=data.iter().filter(|(_,at,m)|[0xf8,0xf1].contains(&m[0]) && at.duration_since(base)>=Duration::from_millis(500) && at.duration_since(base)<Duration::from_millis(600)).map(|(due,at,m)|(m[0],due.duration_since(base).as_micros(),at.duration_since(base).as_micros(),at.saturating_duration_since(*due).as_micros())).collect::<Vec<_>>();
    eprintln!("A-10 recovered_first_100ms=opcode_due_handed_late_us {recovery:?}");
    for code in [0xf8,0xf1] {
        let stale:Vec<_>=recovery.iter().filter(|(op,due,_,_)|*op==code && *due<500000).collect();
        eprintln!("A-10 opcode={code:x} handed_after_reset_with_past_deadline={} worst_handoff_late_us={}",stale.len(),stale.iter().map(|m|m.3).max().unwrap_or(0));
    }
    let peaks=offsets.map(|x|x.into_iter().map(i64::abs).max().unwrap());
    eprintln!("A-10/D-4 warnings_ms={warnings:?} waiting_ms={waiting} clock_mtc_max_grid_error_us={peaks:?} pre_roll=24000 post_roll_end={end} full_before_first_q={first}/{first_q}");
    assert_eq!(waiting,200);assert!(peaks.iter().all(|v|*v<=1000));
}
