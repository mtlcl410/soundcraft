from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress')
for folder in ['lead','lead-fix']:
 p=d/folder/'crates/playback/src/clock_follow/render_lead.rs';s=p.read_text().replace('end=last+RATE*90/1000','end=last+RATE*140/1000');p.write_text(s)
p=d/'lead-fix/crates/playback/src/clock_follow/render_lead.rs';s=p.read_text()
s=s.replace('fn render(bpm:i64, buf:usize, lead_ms:i64, clicks:bool, follow:bool)','''#[derive(Clone,Copy,Debug,Eq,PartialEq)]
enum Policy { Reference, Hard, Predict }

fn render(bpm:i64, buf:usize, lead_ms:i64, clicks:bool, policy:Policy)''').replace('if follow {','if policy!=Policy::Reference {').replace('Some(DeviceTiming::new(start','(policy!=Policy::Hard).then(||DeviceTiming::new(start');start=s.index('                    let reference=render');end=s.index('\n                }',start)
s=s[:start]+'''                    let reference=render(bpm,buf,lead,clicks,Policy::Reference);
                    let hard=render(bpm,buf,lead,clicks,Policy::Hard);
                    let predict=render(bpm,buf,lead,clicks,Policy::Predict);
                    let small=(buf as i64)*bpm*24 < RATE*60;
                    let expected=bursts(&reference);
                    assert_eq!(expected.len(),(if clicks {EIGHTHS/2} else {EIGHTHS}) as usize);
                    for (policy,pcm) in [(Policy::Hard,&hard),(Policy::Predict,&predict)]{
                        let actual=bursts(pcm);
                        let errors:Vec<_>=actual.iter().zip(&expected).map(|(&(on,_),&(at,_))|on as i64-at as i64).collect();
                        let intact=actual.iter().zip(&expected).filter(|&(&(on,off),&(at,end))| pcm[on..off]==reference[at..end]).count();
                        eprintln!("lead bpm={bpm} frames={buf} ms={lead} clicks={clicks} policy={policy:?} count={}/{} intact={intact} samples={errors:?}",actual.len(),expected.len());
                        all &= actual.len()==expected.len() && intact==expected.len();
                        if !small && policy==Policy::Predict {
                            all &= errors.iter().all(|e| *e == 0);
                        }
                    }
                    if small { assert_eq!(predict,hard,"short callbacks must retain the strict horizon"); }'''+s[end:]
s+='''
#[test]
fn prediction_stops_at_the_first_overdue_or_slow_pulse() {
    let feed=MidiFeed::default();
    feed.set_clock_follow(Some(1),true,0,false);
    feed.set_clock(0);
    feed.receive(1,&[0xfa]);
    for pulse in 0..=48 {
        feed.set_clock(pulse*10_000);
        feed.receive(1,&[0xf8]);
    }
    let hard=feed.clock_render_tick().unwrap();
    assert!(feed.clock_render_tick_for_output(489_999,42_667,550_000).unwrap()>hard);
    assert_eq!(feed.clock_render_tick_for_output(490_001,42_667,550_000),Some(hard));
    feed.set_clock(493_000);
    feed.receive(1,&[0xf8]);
    assert_eq!(feed.clock_render_tick_for_output(493_000,42_667,550_000),feed.clock_render_tick());
    feed.receive(1,&[0xfc]);
    assert_eq!(feed.clock_render_tick_for_output(493_000,42_667,550_000),feed.clock_render_tick());
}
'''
p.write_text(s)

