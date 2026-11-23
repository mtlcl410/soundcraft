use super::*;
use soundcraft_model::{Clip, SourceId, SourceAudio, TrackKind, ChannelFormat, Insert};
use soundcraft_playback::midi::MidiInputs;
use std::{sync::{Arc,atomic::{AtomicBool,Ordering}},time::{Duration,Instant}};

#[test]
#[ignore = "real-time 150-track software load benchmark; run serially"]
fn scenario_c7_chase_under_150_track_load(){
    const SR:usize=48000; const BLOCK:usize=128;
    let mut failed=Vec::new(); for inserts in [0, 2, 6] { if std::env::var("SCENARIO_C7_INSERTS").ok().and_then(|n|n.parse::<usize>().ok()).is_some_and(|n|n!=inserts){continue;}
        let mut host=SoundApp::new(Default::default(),None,crate::Services::default());
        host.run("setup.session",json!({"frame_rate":"25"})).unwrap();
        host.engine.session_mut().timecode_start=0; host.midi_inputs=Some(MidiInputs::with_port_names(vec![],vec!["Desk".into()]));
        host.run("setup.mtc",json!({"input":"Desk","online":true,"freewheel":"none"})).unwrap();
        host.service_mtc_chase();
        let feed=host.midi_inputs.as_ref().unwrap().feed().clone();
        let src=feed.ports().assign("Desk");
        let s=host.engine.session_mut(); let src_id=SourceId(27000);
        let pcm=(0..4*SR).map(|i| ((i%128) as f32/128.-0.5)*0.001).collect();
        s.pool.insert(src_id,Arc::new(SourceAudio::new(craft_audio::AudioBuffer{sample_rate:48000,channels:vec![pcm]})));
        for _ in 0..150{
            let id=s.add_track(TrackKind::Audio,ChannelFormat::Mono,None);
            let clip=s.new_clip_id(); let t=s.track_mut(id).unwrap();
            t.playlist_mut().unwrap().clips.push(Clip::audio(clip,"backing",src_id,0,0,4*SR as i64));
            for slot in t.mixer.inserts.iter_mut().take(inserts){*slot=Some(Insert::new("compressor"));}
        }
        let scene=host.engine.session_arc();
        let mut render=soundcraft_mix::RangeRender::new(&scene,None,soundcraft_time::Range::new(0,4*SR as i64),BLOCK);
        let stop=Arc::new(AtomicBool::new(false));let signal=stop.clone();let origin=Instant::now();
        let driver=std::thread::spawn(move||{
            let mut q=0u64;
            while !signal.load(Ordering::Relaxed){
                let due=origin+Duration::from_millis(q*10);
                std::thread::sleep(due.saturating_duration_since(Instant::now()));
                let frames=(q/8)*2;let f=frames%25;let secs=(frames/25)%60;let mins=(frames/1500)%60;
                let data=[f&15,f>>4,secs&15,secs>>4,mins&15,mins>>4,0,2];
                feed.receive(src,&[0xf1,(((q%8)<<4)|data[(q%8) as usize]) as u8]);q+=1;
            }
            q
        });
        let budget=Duration::from_secs_f64(BLOCK as f64/SR as f64);
        let mut peak=0f32;let mut elapsed=Vec::new();let mut statuses=std::collections::BTreeMap::new();let mut lock=false;let mut losses=0;let mut prev=false;
        for _ in 0..4*SR/BLOCK{
            let block=Instant::now();let Some((y,n))=render.next_block(&scene) else{break;};
            for v in &y[0][..n]{peak=peak.max(v.abs());}
            host.service_mtc_chase();host.handle_transport(n as f32/SR as f32);
            *statuses.entry(host.mtc_status).or_insert(0usize)+=1;let now=host.mtc_status=="Locked";
            if prev && !now{losses+=1;} lock|=now;prev=now;
            let load=block.elapsed();elapsed.push(load.as_secs_f64()/budget.as_secs_f64());std::thread::sleep(budget.saturating_sub(load));
        }
        stop.store(true,Ordering::Relaxed);let q=driver.join().unwrap();
        elapsed.sort_by(f64::total_cmp);let len=elapsed.len();
        eprintln!("C7 inserts={inserts} tracks=150 actual_wall_s={:.2} pcm_peak={peak} blocks={len} budget_ms={:.3} render_host_budget_median_pct={:.1} p95_pct={:.1} max_pct={:.1} software_deadline_misses={} QF={q} acquired={lock} lock_losses={losses}",origin.elapsed().as_secs_f64(),budget.as_secs_f64()*1000.,100.*elapsed[len/2],100.*elapsed[len*95/100],100.*elapsed[len-1],elapsed.iter().filter(|x|**x>1.).count());
        eprintln!("C7 statuses={statuses:?}"); if !(peak>0.&&lock&&losses==0){failed.push(inserts);}
    }
    assert!(failed.is_empty(),"lock or PCM failures, inserts {failed:?}");
}

#[test]
fn scenario_d4_transport_publishes_preroll_and_postroll_boundaries() {
    let mut app=SoundApp::new(Default::default(),None,crate::Services::default());
    let edit=&mut app.engine.session_mut().edit;
    edit.pre_post_roll=true;edit.pre_roll=24000;edit.post_roll=12000;
    edit.selection=soundcraft_time::Range::new(96000,192000);
    app.play_from_selection();
    eprintln!("D4 selection=96000..192000 simulated_output_transport={:?}",app.sim);
    assert_eq!(app.sim,Some((72000,Some(204000),None)));
}

