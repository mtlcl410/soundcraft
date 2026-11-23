use super::*;
use super::sampler_song::sampler_song;
use soundcraft_model::ClipContent;
use std::io::{BufWriter,Write};
use std::fs::File;

const ORIGIN:i64=20_000;
fn sample(us:i64)->i64{(us*48+500)/1000}
fn encoded_song(bpm:f64,n:usize,end:i64)->soundcraft_model::Session{
    let mut s=sampler_song(TempoMap::new(bpm,4,4).unwrap(),SampleRate::HZ_48000,n,end);
    let clip=&mut s.tracks[0].playlist_mut().unwrap().clips[0];
    let ClipContent::Midi{sequence}=&mut clip.content else {unreachable!()};
    for (i,n) in sequence.notes.iter_mut().enumerate(){n.velocity=8+(i%120) as u8;}
    s
}
fn bursts(pcm:&[f32])->Vec<(usize,usize)>{
    let mut hits=Vec::<(usize,usize)>::new();
    for (i,v) in pcm.iter().enumerate(){if v.abs()>0.000001{
        if let Some(last)=hits.last_mut() && i-last.1<=6 { last.1=i+1; }else{hits.push((i,i+1));}
    }}
    hits
}
#[test]
#[ignore="manual DJ response audit with local stimulus"]
fn local_dj_scenario_matrix(){
    let dir=std::path::PathBuf::from(std::env::var("DJ_AUDIT").unwrap());
    let out=|s:&str|BufWriter::new(File::create(dir.join(s)).unwrap());
    let mut notes=out("notes.csv");let mut summary=out("cases.csv");let mut states=out("transitions.csv");
    writeln!(notes,"case,eighth,ref_sample,on_sample,error_samples,error_ms,tail_samples,template_match,status").unwrap();
    writeln!(summary,"case,bpm,cut_pulse,ending,coast,expected,matched,missing,duplicates,after_last_f8_extra,damaged,steps,dropouts_total,dropouts_before_terminal,last_state,peak_affected_ms,first_off_ms,first_beat_ms,max_gap_ms,terminal_sample").unwrap();
    writeln!(states,"case,at_us,pulse,kind,state,dropouts,step_intervals,fitted_bpm,ms_since_previous_f8").unwrap();
    let sr=SampleRate::HZ_48000;
    let mut templates=Vec::<Vec<f32>>::new();
    {
        let song=encoded_song(128.,120,48_000*32);
        let mut mix=soundcraft_mix::MixEngine::new(48000.,128);
        let mut block=vec![vec![0.;128];2];
        let mut pcm=Vec::new();
        for start in (0..1400000).step_by(128){mix.render_with_clock_limit(&song,start,128,&mut block,None);pcm.extend_from_slice(&block[0]);}
        for (i,j) in bursts(&pcm){templates.push(pcm[i..j].to_vec());}
        assert_eq!(templates.len(),120);
        for (i,t) in templates.iter().enumerate(){assert_eq!(t.len(),96);assert_ne!(t, &templates[(i+1)%120]);}
    }
    let input=std::fs::read_to_string(dir.join("stimulus.tsv")).unwrap();
    for l in input.lines(){
        let f:Vec<_>=l.split('\t').collect(); let name=f[0];let bpm=f[1].parse::<f64>().unwrap();
        let cut:usize=f[2].parse().unwrap();let ending=f[3];let coast=f[4]=="1";
        let mut pulses:Vec<i64>=f[5].split(',').map(|x|x.parse().unwrap()).collect();
        let last=*pulses.last().unwrap();let expected:Vec<i64>=pulses.iter().step_by(12).map(|x|sample(*x)).collect();
        // Leave four scored tag identities in the clip beyond the source's final F8 only in loss/Stop cases.
        let extend=matches!(ending,"stop"|"silent");
        let end=last+if extend{3_000_000}else{15_000};
        let measured_maxgap=pulses.windows(2).map(|w|w[1]-w[0]).max().unwrap();
        if !extend { let period=pulses[pulses.len()-1]-pulses[pulses.len()-2]; for _ in 0..24 {pulses.push(pulses.last().unwrap()+period);} }
        let end=if extend {end}else{pulses.last().unwrap()+15_000};
        let mut song=encoded_song(bpm,expected.len()+if extend{4}else{0},sample(end)+48_000);
        if let Some((_, tag))=name.split_once('~'){
            let id:usize=tag.parse().unwrap();
            let clip=&mut song.tracks[0].playlist_mut().unwrap().clips[0];
            let ClipContent::Midi{sequence}=&mut clip.content else {unreachable!()};
            sequence.notes[id].velocity-=1;
        }
        let inputs=MidiInputs::with_port_names(vec![],vec!["DJ".into()]);
        let feed=inputs.feed();let port=feed.ports().assign("DJ");
        feed.set_clock_follow(Some(port),coast,0,false);feed.set_clock(ORIGIN);feed.receive(port,&[0xfa]);
        let mut mix=soundcraft_mix::MixEngine::new(48000.,128);
        let mut block=vec![vec![0.;128];2];let mut pcm=Vec::<f32>::new();
        let mut actions=Vec::new();let mut running=true;let mut prevstate=State::Waiting;let mut steps=0;let mut losses=0;
        let mut preloss=0;let mut idx=0;let mut lastwire=0;let mut stop_sent=false;let mut now=0;
        loop{
            let wire=pulses.get(idx).copied()==Some(now);
            feed.set_clock(ORIGIN+now);
            if wire{feed.receive(port,&[0xf8]);}
            if ending=="stop" && now==last+3000{feed.receive(port,&[0xfc]);stop_sent=true;}
            let snap=feed.clock_follow_status(&mut actions);
            for act in actions.drain(..) {match act{Action::Stop=>running=false,Action::Play{..}|Action::Started{..}=>running=true,_=>{}}}
            if wire && snap.step_intervals>0{steps+=1;}
            if snap.state!=prevstate || (wire && snap.step_intervals>0)||losses!=snap.dropouts{
                writeln!(states,"{name},{now},{idx},{},{:?},{},{},{:.5},{:.3}",if wire{"F8"}else{"poll"},snap.state,snap.dropouts,snap.step_intervals,snap.bpm.unwrap_or(0.),(now-lastwire) as f64/1000.).unwrap();
            }
            prevstate=snap.state;losses=snap.dropouts;
            if now<=last{preloss=losses;}
            if wire{lastwire=now;idx+=1;
                update_grid(&mut song.tempo,Some((0,ORIGIN)),0,snap,sr,sample(now+30_000));
            }
            if now>=end{break;}
            let mut next=pulses.get(idx).copied().unwrap_or(end);
            // Poll during silent intervals to observe actual timeout before another F8 can mask it;
            // all intervals >75 ms get deterministic 1 ms polling. No fabricated F8.
            if next-lastwire>75_000{next=next.min(now+1000);}
            if ending=="stop" && !stop_sent{next=next.min(last+3000);}
            while (pcm.len() as i64)<sample(next){
                let pos=pcm.len() as i64;let n=(sample(next)-pos).min(128) as usize;
                if running{mix.render_with_clock_limit(&song,pos,n,&mut block,feed.clock_render_tick());pcm.extend_from_slice(&block[0][..n]);}
                else{pcm.resize(pcm.len()+n,0.);}
            }
            now=next;
        }
        if std::env::var_os("DJ_DIFFERENTIAL").is_some(){
            let raw=pcm.iter().flat_map(|x|x.to_le_bytes()).collect::<Vec<_>>();
            std::fs::write(dir.join(format!("{name}.f32")),raw).unwrap();
        }
        let mut slots=vec![Vec::<(usize,usize,bool)>::new();expected.len()+if extend{4}else{0}];
        let mut extras=0;let mut damage=0;
        for (on,off) in bursts(&pcm){
            let burst=&pcm[on..off];let id=templates.iter().position(|t|t.as_slice()==burst);
            let intact=id.is_some();
            let tag=id.unwrap_or_else(||templates.iter().enumerate().min_by(|(_,a),(_,b)| (a[0]-burst[0]).abs().total_cmp(&(b[0]-burst[0]).abs())).unwrap().0);
            if !intact{damage+=1;let path=dir.join(format!("wave-{name}-{on}-tag{tag}.txt"));let mut dump=BufWriter::new(File::create(path).unwrap());for n in 0..burst.len().max(templates[tag].len()){writeln!(dump,"{} {} {}",n,burst.get(n).unwrap_or(&0.),templates[tag].get(n).unwrap_or(&0.)).unwrap();}}
            let mut possible=(tag..slots.len()).step_by(120).collect::<Vec<_>>();
            let period_tail=pulses[pulses.len()-1]-pulses[pulses.len()-2];
            let at=|i:usize|expected.get(i).copied().unwrap_or_else(||sample(last+((i*12+1-pulses.len()) as i64)*period_tail));
            possible.sort_by_key(|i|(on as i64-at(*i)).abs());
            let i=possible[0];if i>=expected.len(){extras+=1;}
            slots[i].push((on,off,intact));
        }
        let mut missing=0;let mut dups=0;let mut peak=0_f64;let mut offs=[None;2];
        let first=2*(cut/24)+1+if cut%24>=12 {2}else{0}; let next_beat=2*(cut/24+1);
        for (i,s) in slots.iter().enumerate(){
            if i<expected.len() && s.is_empty(){missing+=1;writeln!(notes,"{name},{i},{},,,,,,missing",expected[i]).unwrap();}
            for (copy,&(on,off,ok)) in s.iter().enumerate(){dups+=usize::from(copy>0);
                if i>=expected.len(){writeln!(notes,"{name},{i},,{on},,,{},{ok},post-source",off-on).unwrap();continue;}
                let err=on as i64-expected[i];let ms=err as f64/48.;
                if i*12>=cut{peak=peak.max(ms.abs());}
                if i==first{offs[0]=Some(ms);} if i==next_beat{offs[1]=Some(ms);}
                writeln!(notes,"{name},{i},{},{on},{err},{ms:.6},{},{ok},{}",expected[i],off-on,if copy==0{"hit"}else{"duplicate"}).unwrap();
            }
        }
        let maxgap=measured_maxgap;
        writeln!(summary,"{name},{bpm},{cut},{ending},{coast},{},{},{missing},{dups},{extras},{damage},{steps},{losses},{preloss},{prevstate:?},{peak:.6},{},{},{:.3},{}",expected.len(),expected.len()-missing,offs[0].map_or(String::new(),|x|format!("{x:.6}")),offs[1].map_or(String::new(),|x|format!("{x:.6}")),maxgap as f64/1000.,sample(last)).unwrap();
        notes.flush().unwrap();summary.flush().unwrap();states.flush().unwrap();
    }
}
