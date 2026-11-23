from pathlib import Path
p=Path("crates/engine/src/lib.rs")
s=p.read_text(encoding='utf8')
a=s.index("fn migrate_mtc_settings(")
b=s.index("impl Default for Engine",a)
s=s[:a]+'''/// Recover malformed fields independently before accepting the project for chase.
fn migrate_mtc_settings(s: &mut Session) -> Vec<String> {
    let mut notes = Vec::new();
    let frames_key = "midi.mtc.freewheel_frames";
    if let Some(frames) = s.edit.values.get_mut(frames_key)
        && (!(4.0..=40.0).contains(frames) || frames.fract() != 0.)
    {
        notes.push(format!("The session's Freewheel frames value ({frames_key} = {frames}) was out of range and was reset to 8."));
        *frames = 8.;
    }

    let mut modes = s.edit.flags.iter().filter_map(|flag| flag.strip_prefix(MTC_FREEWHEEL));
    let mode = modes.next();
    let has_mode = mode.is_some();
    if let Some(mode) = mode
        && (!matches!(mode, "none" | "frames" | "jam_sync") || modes.next().is_some())
    {
        notes.push(format!("The session's Freewheel mode (midi.mtc.freewheel_mode = {mode}) was invalid or ambiguous and was reset to Frames."));
        s.edit.flags.retain(|flag| !flag.starts_with(MTC_FREEWHEEL));
        s.edit.flags.insert(format!("{MTC_FREEWHEEL}frames"));
    }
    if s.edit.flags.remove("midi.mtc.jam_sync") && !has_mode {
        s.edit.flags.insert(format!("{MTC_FREEWHEEL}jam_sync"));
    }

    let limit = s.sample_rate.samples(3600.);
    let external_key = "sync.external_offset";
    if let Some(offset) = s.edit.values.get_mut(external_key)
        && (!offset.is_finite() || offset.fract() != 0. || offset.abs() > limit as f64)
    {
        notes.push(format!("The session's External Timecode Offset ({external_key} = {offset} samples) was invalid and was reset to 0."));
        *offset = 0.;
    }
    let legacy_key = "midi.mtc.external_offset_frames";
    let Some(&frames) = s.edit.values.get(legacy_key) else { return notes };
    // Convert only bounded integral frame counts and apply the final limit in samples,
    // as Session Setup does for fractional frame rates.
    let samples = (frames.fract() == 0. && frames.abs() <= 5_184_000.)
        .then(|| s.frame_rate.samples_at_frame(frames as i64, s.sample_rate))
        .filter(|samples| samples.unsigned_abs() <= limit as u64);
    let Some(samples) = samples.map(|samples| samples as f64) else {
        notes.push(format!("The session's legacy reader offset ({legacy_key} = {frames} frames) was invalid and was reset to 0."));
        s.edit.values.remove(legacy_key);
        return notes;
    };
    let existing = s.edit.value(external_key, 0.);
    if existing != 0. && samples != 0. && existing != samples {
        notes.push("The session has conflicting timecode offsets. Chase uses the External Timecode Offset.".into());
    } else {
        if existing == 0. {
            s.edit.values.insert(external_key.into(), samples);
        }
        s.edit.values.remove(legacy_key);
        notes.push("Migrated the MTC reader offset to External Timecode Offset.".into());
    }
    notes
}

'''+s[b:]
s=s.replace('migrate_mtc_settings(&mut session).map(str::to_owned).into_iter().collect()', 'migrate_mtc_settings(&mut session)').replace('if let Some(note) = migrate_mtc_settings(&mut s) {', 'for note in migrate_mtc_settings(&mut s) {')
p.write_text(s,encoding='utf8')
