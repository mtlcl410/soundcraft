from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-large-tempo')
w=d/'work'
def replace(path, old,new):
 p=w/path;s=p.read_text();assert old in s, path;p.write_text(s.replace(old,new))
r='crates/ui-egui/src/app/clock_follow.rs'
replace(r,'let elapsed_at_edit = sr.seconds(edit_sample - start - elapsed);','let elapsed_at_edit = sr.seconds(edit_sample.saturating_sub(start).saturating_sub(elapsed));')
replace(r,'let join = ((ahead / TICKS_PER_PULSE as f64).ceil() as i64 + 1) * TICKS_PER_PULSE;','let join = ((ahead / TICKS_PER_PULSE as f64).ceil() as i64).saturating_add(1).saturating_mul(TICKS_PER_PULSE);\n        if join <= edit { return false; }')
replace('crates/playback/src/sync_input.rs','Oldest point in four consecutive intervals that consistently depart from a previous','Oldest point in a train of consistent intervals that depart from a previous')
replace('crates/playback/src/clock_follow.rs','(self.state == State::Locked).then(|| self.played_pulse.saturating_add(1))','match self.state {\n            State::Locked => Some(self.played_pulse.saturating_add(1)),\n            State::Stopped => Some(self.played_pulse),\n            State::Waiting | State::Coasting => None,\n        }')
replace('crates/mix/src/lib.rs','let start = self.held_score_from.take().unwrap_or(pos);\n        let limit','let limit')
replace('crates/mix/src/lib.rs','let score = Range { start, end: physical_end.min(limit).max(start) };','// At a compensated Continue the first callback may already be ahead of\n        // the wire. Preserve the requested boundary attack and its note-off.\n        let start = self.held_score_from.take().unwrap_or_else(|| {\n            if self.midi_origin.is_some() { pos.min(limit.saturating_sub(1)) } else { pos }\n        });\n        let score = Range { start, end: physical_end.min(limit).max(start) };')
replace('crates/mix/src/lib.rs','if frames > 0 && !self.monitor_only && note_start < score.end','if frames > 0 && !self.monitor_only && score.start < score.end && note_start < score.end')
replace('crates/mix/src/strip.rs','chase_controllers(s, t, pos, inst)','chase_controllers(s, t, blk.score.start, inst)')
q='crates/ui-egui/src/app/clock_follow/tests/'
p=w/(q+'coast_relock.rs');s=p.read_text();begin=s.index('    let mut song');end=s.index('    let pcm =',begin);fixture=s[begin:end];fixture=fixture.replace('sample_rate: 48000','sample_rate: sr.hz()').replace('end + 48000','end.saturating_add(i64::from(sr.hz()))')
(w/(q+'sampler_song.rs')).write_text(s[s.index('use soundcraft_midi'):s.index('use soundcraft_playback')]+'use soundcraft_time::{SampleRate,TempoMap};\nuse std::sync::Arc;\npub(super) fn sampler_song(grid: TempoMap, sr: SampleRate, count: usize,end:i64) -> Session {\n'+fixture+'    song\n}\n')
p.write_text(s[:s.index('use soundcraft_midi')]+'use super::sampler_song::sampler_song;\nuse soundcraft_time::Range;\n'+s[s.index('// Render'):begin]+'    let song=sampler_song(grid, sr, count, end);\n'+s[end:])
p=w/(q+'large_steps.rs');s=p.read_text();p.write_text('use super::*;\nuse super::sampler_song::sampler_song;\n'+s[s.index('fn edges'):].replace('sampler_song(before,count)','sampler_song(TempoMap::new(before,4,4).unwrap(),sr,count,48_000*60)'))
replace(r,'    mod large_steps;','    mod large_steps;\n    mod sampler_song;')
p=w/(q+'large_steps.rs')
with p.open('a') as f:f.write("""
#[test]
fn early_device_render_waits_for_the_wire_and_keeps_the_located_attack() {
    let inputs = MidiInputs::with_port_names(vec![], vec!["drums".into()]);
    let feed = inputs.feed();
    let port = feed.ports().assign("drums");
    feed.set_clock_follow(Some(port), true, 0, false);
    feed.set_clock(0);
    feed.receive(port, &[0xfa]);
    feed.receive(port, &[0xf8]);
    let song = sampler_song(TempoMap::new(120., 4, 4).unwrap(), SampleRate::HZ_48000, 2, 48000);
    let mut mix = soundcraft_mix::MixEngine::new(48000., 128);
    let mut pcm = Vec::new();
    let mut block = vec![vec![0.;128];2];
    // Start rendering 30 ms ahead, with only the first wire pulse in hand.
    let mut pos=1440;
    mix.start_midi_at(0);
    let mut render = |end:i64, pcm:&mut Vec<f32>| {
        while pos<end {
            let n=(end-pos).min(128) as usize;
            mix.render_with_clock_limit(&song,pos,n,&mut block,feed.clock_render_tick());
            pcm.extend_from_slice(&block[0][..n]);
            pos+=n as i64;
        }
    };
    for pulse in 1..=10 {
        render(1440 + pulse*1000,&mut pcm);
        feed.set_clock(pulse*1_000_000/48);
        feed.receive(port,&[0xf8]);
    }
    render(14000,&mut pcm);
    assert_eq!(edges(&pcm,0),vec![(0,96)], "the second hat must wait for pulse 11");
    feed.set_clock(280_000);
    feed.receive(port,&[0xf8]);
    render(14400,&mut pcm);
    let hits=edges(&pcm,0);
    assert_eq!(hits.len(),2);
    assert!(hits[1].0>=14000-1440);
    assert_eq!(hits[1].1-hits[1].0,96);
    assert_eq!(&pcm[..96],&pcm[hits[1].0 as usize..hits[1].1 as usize]);
}
""")
for base in [w,d/'tree']:
 p=base/'crates/playback/src/clock_follow/tests.rs';s=p.read_text();t='let p95 = errors[errors.len() * 95 / 100];';p.write_text(s.replace(t,t+'\n            eprintln!("steady {bpm} {jitter} BPMp95={p95:.8} phasep95_us={:.4}",phase_errors[phase_errors.len()*95/100]);'))

