from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress')
p=d/'ramps/crates/ui-egui/src/app/clock_follow/tests/ramp_response.rs';s=p.read_text()
src=s.index('            let mut seed');s=s[:src]+'''            let mut render_to = |end: i64, song: &soundcraft_model::Session| {
                while (pcm.len() as i64) < end {
                    let start = pcm.len() as i64;
                    let frames = (end - start).min(128) as usize;
                    mix.render_with_clock_limit(song, start, frames, &mut block, feed.clock_render_tick());
                    pcm.extend_from_slice(&block[0][..frames]);
                }
            };
'''+s[src:]
b=s.index('                while (pcm.len() as i64) < sr.samples');e=s.index('                feed.set_clock(at',b);s=s[:b]+'''                // Render up to the next arrival with only the previous packet available.
                render_to(sr.samples(at as f64 / 1e6), &song);
'''+s[e:]
b=s.index('            while (pcm.len() as i64) < end',s.index('let end = expected'));e=s.index('            let mut edges =',b);s=s[:b]+'            render_to(end, &song);\n'+s[e:];s=s.replace('                    if i >= 24 && snap.state','                    // The tempo estimator acquires within one beat. Ignore the initial estimate.\n                    if i >= 24 && snap.state')
p.write_text(s)
p=d/'ramps/crates/playback/src/clock_follow/tests.rs';s=p.read_text();start=s.index('fn locks_and_predicts_pulses_across_tempos_jitter_and_usb_quantization');i=s.index('if pulse >= 240 {',start);s=s[:i]+'''if pulse >= 24 {
                    assert!(!r.steady.is_tempo_ramp(), "false ramp at {bpm} BPM/{jitter} us, pulse {pulse}");
                }
                '''+s[i:];p.write_text(s)

