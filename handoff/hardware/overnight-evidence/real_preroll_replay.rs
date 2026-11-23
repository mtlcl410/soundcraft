use super::*;
use crate::midi::MidiFeed;
use soundcraft_model::{ChannelFormat, Clip, SourceAudio, SourceId, TrackKind};

#[test]
fn replay_same_wire_with_and_without_stopped_locate() {
    let text = std::fs::read_to_string(std::env::var("SC_FULL_TAKE_DATA").unwrap()).unwrap();
    let mut lines=text.lines(); let mut reference=None;
    while let Some(header)=lines.next() {
        let h: Vec<_>=header.split_whitespace().collect();
        let rate=match h[2]{"24"=>FrameRate::Fps24,"25"=>FrameRate::Fps25,"30"=>FrameRate::Fps30,"29.97df"=>FrameRate::Fps29_97Drop,"29.97nd"=>FrameRate::Fps29_97,_=>panic!()};
        let frame=h[3].parse().unwrap(); let score:usize=h[5].parse().unwrap();
        let events:Vec<(i64,u8)>=lines.next().unwrap().split_whitespace().map(|z|{let (a,b)=z.split_once(':').unwrap();(a.parse().unwrap(),b.parse().unwrap())}).collect();
        let mut s=session(rate);
        let t=s.add_track(TrackKind::Audio,ChannelFormat::Mono,None);
        let mut wave=vec![0.;score+16*24_000];
        for i in 0..16 {
            for j in 0..127 {
                wave[score+24_000*i+j]=if ((i>>(j%4))&1)==1 {0.3}else{-0.3};
            }
        }
        let len=wave.len() as i64;
        s.pool.insert(SourceId(1),Arc::new(SourceAudio::new(craft_audio::AudioBuffer{sample_rate:48_000,channels:vec![wave]})));
        let id=s.new_clip_id();s.track_mut(t).unwrap().playlist_mut().unwrap().clips.push(Clip::audio(id,"tags",SourceId(1),0,0,len));
        let (mut audio,commands,_)=callback(s,48000.);
        let feed=Arc::new(MidiFeed::default());feed.set_mtc_source(Some(0));
        commands.send(Cmd::Midi(feed.clone())).unwrap();feed.set_clock(0);if h[1]=="located" {feed.receive(0,&locate(frame,rate));}
        let mut k=0;let base=Instant::now();let mut tag=Vec::new();let mut hits=[0;16];let mut partial=0; let mut onset=None;
        for us in lines.next().unwrap().split_whitespace().map(|v|v.parse::<i64>().unwrap()){
            while k<events.len() && events[k].0<=us {feed.set_clock(events[k].0);feed.receive(0,&[0xf1,events[k].1]);k+=1;}
            feed.set_clock(us);audio.device_buffer_frames=256;
            audio.device_timing=Some(DeviceTiming::new(base+Duration::from_micros(us as u64),Some(Duration::from_micros(15166)),0));
            let mut pcm=[0.;512];audio.fill(&mut pcm,2);
            for (i,pair) in pcm.chunks_exact(2).enumerate(){
                if pair[0].abs()>0.03 {onset.get_or_insert(us+i as i64*1_000_000/48_000);tag.push(pair[0]>0.);}
                else if !tag.is_empty(){
                    if tag.len()==127 && tag.iter().enumerate().all(|(idx,v)| *v==tag[idx%4]){
                        let id=(0..4).fold(0,|n,i| n | ((tag[i] as usize)<<i));hits[id]+=1;
                    }else{partial+=1;}
                    tag.clear();
                }
            }
        }
        assert!(tag.is_empty());
        println!("PAIR,{},{},{},{partial},{hits:?}",h[0],h[1],onset.unwrap());
        assert_eq!(partial,0);
        if h[1]=="rolling" { reference=onset; }
        else {
            assert!(onset.unwrap().abs_diff(reference.unwrap()) <= 21, "stopped locate changes first onset by {} us", onset.unwrap()-reference.unwrap());
        }
        assert_eq!(hits,[1;16]);
    }
}
