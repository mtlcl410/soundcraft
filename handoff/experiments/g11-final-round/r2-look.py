exec((d/'r2-pending.py').read_text(encoding='utf-8-sig'))
s=s.replace('        let ahead = (edit as f64).max(wire_at_edit);', '''        if s.recovering_tempo_step && !s.braking && !s.packed_delivery &&
            grid.tempos().last().is_some_and(|last| last.tick>edit && (last.bpm-bpm).abs()<bpm*0.02 &&
            (sr.seconds(grid.tick_to_samples(last.tick,sr)-edit_sample)-(last.tick as f64 - wire_at_edit)*60./(bpm*TICKS_PER_QUARTER as f64)).abs()<0.002) {return false;}
        let ahead = (edit as f64).max(wire_at_edit);''')
