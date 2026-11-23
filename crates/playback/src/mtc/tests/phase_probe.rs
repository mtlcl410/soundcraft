use std::collections::BTreeMap;
use super::*;
use crate::midi::MidiFeed;
use soundcraft_model::{ChannelFormat, Clip, SourceAudio, SourceId, TrackKind};

fn replay(rate: FrameRate, locate_frame: i64, at: usize, score: usize, events: &[(i64,u8)], times: &[i64]) -> Vec<(i64, i64)> {
    let mut s=session(rate);
    let t=s.add_track(TrackKind::Audio,ChannelFormat::Mono,None);
    let mut wave=vec![0.;at+96000];
    // Distinguish a skipped predecessor, the protected downbeat and a later marker.
    if at>1000 {wave[at-1000..at-995].fill(0.5);}
    for k in [at,score,at+24000] {wave[k..k+5].fill(0.5);}
    let len=wave.len() as i64;
    s.pool.insert(SourceId(1),Arc::new(SourceAudio::new(craft_audio::AudioBuffer{sample_rate:48000,channels:vec![wave]})));
    let id=s.new_clip_id();s.track_mut(t).unwrap().playlist_mut().unwrap().clips.push(Clip::audio(id,"markers",SourceId(1),0,0,len));
    let (mut audio,commands,_)=callback(s,48000.);
    let feed=Arc::new(MidiFeed::default());feed.set_mtc_source(Some(0));
    commands.send(Cmd::Midi(feed.clone())).unwrap();
    feed.set_clock(0);feed.receive(0,&locate(locate_frame,rate));
    let base=Instant::now();let mut j=0;let mut hits=Vec::new();let mut loud=false;
    for (index,&us) in times.iter().enumerate() {
        while j<events.len() && events[j].0<=us {
            feed.set_clock(events[j].0);feed.receive(0,&[0xf1,events[j].1]);j+=1;
        }
        feed.set_clock(us);
        audio.device_buffer_frames=256;
        audio.device_timing=Some(DeviceTiming::new(base+Duration::from_micros(us as u64),Some(Duration::from_micros(15166)),0));
        let mut pcm=[0.;512];audio.fill(&mut pcm,2);
        for (k,pair) in pcm.chunks_exact(2).enumerate() {
            let high=pair[0].abs()>0.03;
            if high && !loud {hits.push((us+(k as i64*1000000+24000)/48000,(index*256+k) as i64));}
            loud=high;
        }
    }
    assert_eq!(hits.len(),3,"unexpected attacks at locate {at}: {hits:?}");
    assert_eq!(hits[2].1-hits[0].1,24000,"anchor and half-second interval");
    assert_eq!(hits[1].1-hits[0].1,(score-at) as i64);
    hits
}

#[test]
fn anchored_phase_replay_matrix() {
    let mut lines=include_str!("../phase_replay_inputs.txt").lines();
    let mut groups=BTreeMap::<String,Vec<i64>>::new();
    let mut swept=Vec::new();
    while let Some(line)=lines.next() {
        let h:Vec<_>=line.split_whitespace().collect();
        let rate=match h[2] { "24"=>FrameRate::Fps24,"25"=>FrameRate::Fps25,"29.97nd"=>FrameRate::Fps29_97,"29.97df"=>FrameRate::Fps29_97Drop,"30"=>FrameRate::Fps30,_=>panic!() };
        let frame=h[3].parse().unwrap();let at=h[4].parse().unwrap();let score=h[5].parse().unwrap();
        let reference:i64=h[6].parse().unwrap();
        let events=lines.next().unwrap().split_whitespace().map(|s| {let (a,b)=s.split_once(':').unwrap();(a.parse().unwrap(),b.parse().unwrap())}).collect::<Vec<_>>();
        let times=lines.next().unwrap().split_whitespace().map(|v|v.parse().unwrap()).collect::<Vec<i64>>();
        let hits=replay(rate,frame,at,score,&events,&times);
        let err=hits[1].0-reference;
        println!("TRACE,{},{},{err},{}",h[0],h[1],h[7]);
        groups.entry(h[0].into()).or_default().push(err);
        if h[0]=="h4a-integration-30-forward-01" && h[1]=="0" {
            for phase in 0..256 {
                let regular=(0..177).map(|i|((i*256+phase)*1000000+24000)/48000).collect::<Vec<_>>();
                swept.push(replay(rate,frame,at,score,&events,&regular)[1].0);
            }
        }
    }
    let sweep=swept.iter().max().unwrap()-swept.iter().min().unwrap();
    println!("PHASE_US,{sweep}");
    for (group,values) in &groups {println!("SPREAD_US,{group},{}",values.iter().max().unwrap()-values.iter().min().unwrap());}
    assert!(sweep<=21,"one-sample phase sweep: {sweep} us");
    assert!(groups.values().all(|v|v.len()==10 && v.iter().max().unwrap()-v.iter().min().unwrap()<=3000));
}
