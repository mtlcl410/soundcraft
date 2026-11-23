"""Replay captured Model 12 QFs and ASIO callback times on the pure #1663 playback code, entirely offline."""
from pathlib import Path
import csv,json,os,subprocess,sys
from manual_run import hw, save
from m1 import np
def main():
    d=hw/'runs/h4b-model12-02'
    out=hw/'software-h4b'
    out.mkdir(exist_ok=True)
    tree=out/'owner'
    base=hw.parent/'g11-final-round/mtc'
    if not tree.exists():subprocess.run(['git','-C',base,'worktree','add','--detach',tree,'bab99312'],check=True)
    head=subprocess.check_output(['git','-C',tree,'rev-parse','HEAD'],text=True).strip()
    assert head.startswith('bab99312')
    source=tree/'crates/playback/src/mtc/tests.rs'
    base_text=subprocess.check_output(['git','-C',tree,'show','HEAD:crates/playback/src/mtc/tests.rs']).decode()
    initial=source.read_text('utf8')
    if initial!=base_text and 'fn model12_acquisition_preserves_four_markers()' not in initial:raise RuntimeError('Unexpected modifications to proof checkout')
    meta=json.loads((d/'driver/epoch-0.json').read_text())
    n=meta['buffer'];fq=meta['qpc_frequency']
    array=np.memmap(d/'driver/epoch-0.bin',dtype=np.dtype([('prefix','V16'),('qpc','<u8'),('rest',f'V{16+8*n}')]),mode='r')
    first=json.loads((d/'segments.json').read_text())[0]['first']
    t0=first-100_000_000
    with (d/'wire.csv').open() as f:
        rows=[(int(r['qpc_ns']),bytes.fromhex(r['hex'])) for r in csv.DictReader(f) if r['hex'].startswith('f1') and t0<=int(r['qpc_ns'])<first+2_500_000_000]
    callbacks=[(int(q)*1_000_000_000//fq-t0)//1000 for q in array['qpc'] if t0<=int(q)*1_000_000_000//fq<first+2_450_000_000]
    data=', '.join(f'({(t-t0)//1000},{m[1]})' for t,m in rows)
    test="""
#[test]
fn model12_acquisition_preserves_four_markers() {
    use crate::midi::MidiFeed;
    use soundcraft_model::{ChannelFormat, Clip, SourceAudio, SourceId, TrackKind};
    let mut s = session(FrameRate::Fps30);
    let track = s.add_track(TrackKind::Audio, ChannelFormat::Mono, None);
    let mut wave = vec![0.; 144000];
    for pos in [12000,36000,60000,84000] { wave[pos..pos+127].fill(0.5); }
    s.pool.insert(SourceId(1), Arc::new(SourceAudio::new(craft_audio::AudioBuffer { sample_rate: 48000, channels: vec![wave] })));
    let id=s.new_clip_id();
    s.track_mut(track).unwrap().playlist_mut().unwrap().clips.push(Clip::audio(id, "acquisition", SourceId(1), 0, 0, 144000));
    let (mut audio,commands,_) = callback(s,48000.);
    let feed=Arc::new(MidiFeed::default());feed.set_mtc_source(Some(0));
    commands.send(Cmd::Midi(feed.clone())).unwrap();
    feed.set_clock(0);feed.receive(0,&locate(0,FrameRate::Fps30));
    let events: &[(i64,u8)] = &[EVENTS];
    let times: &[i64] = &[TIMES];
    let now=Instant::now();let mut j=0;let mut loud=false;let mut attacks=Vec::new();
    for &us in times {
        while j<events.len() && events[j].0<=us {
            feed.set_clock(events[j].0);feed.receive(0,&[0xf1,events[j].1]);j+=1;
        }
        feed.set_clock(us);
        audio.device_timing=Some(DeviceTiming::new(now+Duration::from_micros(us as u64),Some(Duration::from_micros(15166)),0));
        let mut block=[0.;512];audio.fill(&mut block,2);
        for (i,pair) in block.chunks_exact(2).enumerate() {
            let next=pair[0].abs()>0.03;
            if next && !loud {attacks.push(us+i as i64*1000000/48000);}
            loud=next;
        }
    }
    println!("attacks us {attacks:?}, relocates {}",feed.mtc_diagnostics().hard_relocates);
    assert_eq!(attacks.len(),4,"missing coded attack at acquisition");
}
""".replace('EVENTS',data).replace('TIMES',', '.join(map(str,callbacks)))
    source.write_text(base_text+test,encoding='utf8')
    env=os.environ|{'CARGO_TARGET_DIR':str(hw.parent/'g11-follow-r3-target')}
    runner=hw.parent/'g11-a10-recovery/run.cmd'
    args=['cmd','/c',str(runner),'test','--offline','-j','2','-p','soundcraft-playback','--lib','model12_acquisition_preserves_four_markers','--','--nocapture']
    with (out/'replay.log').open('wb') as log:
        rc=subprocess.run(args,cwd=tree,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    text=(out/'replay.log').read_text('utf8',errors='replace')
    save(out/'result.json',dict(head=head,observed_assertion=rc!=0 and 'missing coded attack at acquisition' in text,exit=rc,
         cases=1,quarter_frames=len(rows),callback_count=len(callbacks),messages=[s for s in text.splitlines() if 'attacks us' in s or 'test result:' in s]))
if __name__=='__main__':main()

