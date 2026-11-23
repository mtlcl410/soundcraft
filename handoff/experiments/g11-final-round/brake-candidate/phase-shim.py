from pathlib import Path
p=Path('../brake-candidate/pcm_probe.rs');s=p.read_text().replace('mix.render_clock_block(&song, pos, count, &mut output, feed.clock_render_tick(), feed.clock_delivery());','mix.render_with_clock_limit(&song, pos, count, &mut output, feed.clock_render_tick());')
p.write_text(s)
