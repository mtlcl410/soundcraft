from pathlib import Path
def rep(path,a,b):
 p=Path(path);s=p.read_text('utf8');assert s.count(a)==1,(path,a);p.write_text(s.replace(a,b),'utf8')
e='crates/engine/src/cmd/options.rs'
rep(e,'s.edit.values.insert("sync.external_offset".into(), samples as f64);','s.edit.values.remove("midi.mtc.external_offset_frames");\n        s.edit.values.insert("sync.external_offset".into(), samples as f64);')
p='crates/engine/src/cmd/setup_more.rs'
rep(p,'    if key == "sync.external_offset"\n        && let Some(v) = p.get("timecode")','    let edit = if key == "sync.external_offset"\n        && let Some(v) = p.get("timecode")')
rep(p,'        s.edit.values.insert(key.into(), samples as f64);','        Some(samples as f64)')
rep(p,'        s.edit.values.insert(key.to_string(), (f.clamp(-10_000.0, 10_000.0) * per_frame).round());','        Some((f.clamp(-10_000.0, 10_000.0) * per_frame).round())')
rep(p,'        s.edit.values.insert(key.to_string(), n.clamp(-lim, lim).round());\n    }\n    let samples = s.edit.value(key, 0.0);','''        Some(n.clamp(-lim, lim).round())
    } else {
        None
    };
    if let Some(value) = edit {
        s.edit.values.insert(key.into(), value);
        if key == "sync.external_offset" {
            s.edit.values.remove("midi.mtc.external_offset_frames");
        }
    }
    let samples = s.edit.value(key, 0.0);''')
rep('docs/midi-input.md','Recording while following external MIDI Beat Clock is a separate workflow.','External MIDI Beat Clock following is unavailable in this revision.')
rep('crates/dsp/src/offline.rs','/// `natural`, searched within `tol` of `nominal` (coarse stride 4, then refined +-3).','''/// `natural`, searched within `tol` of `nominal` (coarse stride 4, then refined ±3).
/// Positions and tolerance are in samples. Pass a nonnegative nominal position and tolerance,
/// and a positive overlap length. The guide must handle positions beyond the available signal
/// (for example, by returning zero); the search does not know the guide's length.''')

