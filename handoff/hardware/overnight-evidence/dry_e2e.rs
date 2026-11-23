
#[test]
fn a_dry_lead_in_starts_the_same_pcm_with_a_locate_or_a_rolling_join() {
    use crate::midi::MidiFeed;
    let rate = FrameRate::Fps30;
    let render = |located: bool| {
        let mut s = session(rate);
        let t = s.add_track(TrackKind::Audio, ChannelFormat::Mono, None);
        let mut wave = vec![0.; 100000];
        for k in [12000, 36000, 60000, 84000] {
            wave[k..k+8].fill(0.5);
        }
        let len = wave.len() as i64;
        s.pool.insert(SourceId(1), Arc::new(SourceAudio::new(craft_audio::AudioBuffer { sample_rate:48000, channels:vec![wave] })));
        let id = s.new_clip_id();
        s.track_mut(t).unwrap().playlist_mut().unwrap().clips.push(Clip::audio(id, "guide", SourceId(1), 0, 0, len));
        let (mut audio, tx, _) = callback(s, 48000.);
        let feed = Arc::new(MidiFeed::default());
        feed.set_mtc_source(Some(0));
        tx.send(Cmd::Midi(feed.clone())).unwrap();
        feed.set_clock(0);
        if located { feed.receive(0, &locate(0,rate)); }
        let start = Instant::now();
        let mut piece = 0;
        let mut last = false;
        let mut hits = Vec::new();
        for sample in (0..110000).step_by(256) {
            let now = sample as i64 * 1000000 / 48000;
            while 100000 + piece*1000000/120 <= now {
                feed.set_clock(100000 + piece*1000000/120);
                feed.receive(0,&quarters(2+2*(piece/8),rate)[piece as usize%8]);
                piece+=1;
            }
            feed.set_clock(now);
            audio.device_buffer_frames = 256;
            audio.device_timing = Some(DeviceTiming::new(start+Duration::from_micros(now as u64),Some(Duration::from_micros(15166)),0));
            let mut pcm=[0.;512];
            audio.fill(&mut pcm,2);
            for (offset,pair) in pcm.chunks_exact(2).enumerate() {
                let high=pair[0].abs()>0.03;
                if high && !last { hits.push(sample+offset); }
                last=high;
            }
        }
        hits
    };
    let reference = render(false);
    assert_eq!(reference.len(),4);
    assert!(reference.windows(2).all(|w| w[1]-w[0]==24000));
    assert_eq!(render(true),reference);
}

