from pathlib import Path
w=Path('E:/soundcraft/compatibility-audit/g11-large-tempo/work')
p=w/'crates/ui-egui/src/app/clock_follow/tests/coast_relock.rs'
s=p.read_text();start=s.index('use soundcraft_time::Range;');mid=s.index('    let mut sounding = false;',start);s=s[:start]+'''
// Count attacks in the PCM captured while the MIDI input was arriving.
fn attacks(pcm: &[f32]) -> Vec<i64> {
'''+s[mid:];s=s.replace('pcm[0].iter()', 'pcm.iter()')
s=s.replace('let mut grid = TempoMap::new(120., 4, 4).unwrap();','''let mut song = sampler_song(TempoMap::new(120., 4, 4).unwrap(), sr, 65, 48_000 * 20);
        let mut mixer = soundcraft_mix::MixEngine::new(48_000.,128);
        let mut block = vec![vec![0.;128];2];
        let mut pcm = Vec::new();
        let mut render_to = |end:i64, song:&soundcraft_model::Session| {
            while (pcm.len() as i64)<end {
                let pos=pcm.len() as i64;
                let frames=(end-pos).min(128) as usize;
                mixer.render_with_clock_limit(song,pos,frames,&mut block,feed.clock_render_tick());
                pcm.extend_from_slice(&block[0][..frames]);
            }
        };''')
s=s.replace('            feed.set_clock(stamp);','            if stop.is_none() { render_to(sr.samples(arrival_time), &song); }\n            feed.set_clock(stamp);')
s=s.replace('update_grid(&mut grid,','update_grid(&mut song.tempo,')
s=s.replace('let hits = render_hats(grid, sr, expected.len(), end);','render_to(end,&song);\n        let hits = attacks(&pcm);')
p.write_text(s)
p=w/'crates/ui-egui/src/app/clock_follow.rs';s=p.read_text();assert '    mod performance_scenarios;' in s;p.write_text(s.replace('    mod performance_scenarios;\n',''))
p=w/'crates/ui-egui/src/app/clock_follow/tests/performance_scenarios.rs';(w.parent/'performance_scenarios.rs').write_bytes(p.read_bytes());p.unlink()

