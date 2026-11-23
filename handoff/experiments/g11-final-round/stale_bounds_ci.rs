#[test]
fn stale_clock_clip_bounds_skip_removed_tracks_and_replaced_clip_ids() {
    let mut original = synth_session(-12.);
    let track = original.tracks.iter_mut().find(|t| t.instrument.is_some()).unwrap();
    track.ticks_timebase = true;
    let id = track.id;
    let old_length = track.playlist_mut().unwrap().clips[0].length;
    let bounds = MidiClipBeatBounds::from_score(&original, |_| true);
    let tempo = soundcraft_time::TempoMap::new(60., 4, 4).unwrap();

    // First ensure the cached entry really changes a matching clip at this tempo.
    let mut valid = original.clone();
    bounds.apply(&mut valid, &tempo);
    assert_ne!(valid.track_mut(id).unwrap().playlist_mut().unwrap().clips[0].length, old_length);

    let mut replacement = original.clone();
    let new_id = replacement.new_clip_id();
    replacement.track_mut(id).unwrap().playlist_mut().unwrap().clips[0].id = new_id;
    bounds.apply(&mut replacement, &tempo);
    assert_eq!(replacement.track_mut(id).unwrap().playlist_mut().unwrap().clips[0].length, old_length);

}

#[test]
fn stale_clock_clip_bounds_from_a_removed_track_do_not_panic() {
    let mut original = synth_session(-12.);
    original.tracks.iter_mut().find(|t| t.instrument.is_some()).unwrap().ticks_timebase = true;
    let bounds = MidiClipBeatBounds::from_score(&original, |_| true);
    original.tracks.clear();
    let tempo = original.tempo.clone();
    bounds.apply(&mut original, &tempo);
    assert!(original.tracks.is_empty());
}
