mod bounds {
//! Preserve the musical start and exclusive end of MIDI clips across tempo-map changes.
use soundcraft_model::{ClipContent, ClipId, Session};
use soundcraft_time::{SampleRate, Samples, TempoMap};

#[derive(Clone, Copy)]
struct Anchor {
    tick: i64,
    fraction: f64,
}

impl Anchor {
    fn new(sample: Samples, tempo: &TempoMap, sr: SampleRate) -> Self {
        let nearest = tempo.samples_to_ticks(sample, sr);
        let at = tempo.tick_to_samples(nearest, sr);
        if sample == at {
            return Self { tick: nearest, fraction: 0. };
        }
        // Preserve sub-tick trims, including the distinction between a note exactly
        // at the excluded end and one a sample before it.
        let tick = if sample < at { nearest.saturating_sub(1) } else { nearest };
        let left = tempo.tick_to_samples(tick, sr);
        let right = tempo.tick_to_samples(tick.saturating_add(1), sr);
        let fraction = sample.saturating_sub(left) as f64 / right.saturating_sub(left).max(1) as f64;
        Self { tick, fraction }
    }

    fn sample(self, tempo: &TempoMap, sr: SampleRate) -> Samples {
        let left = tempo.tick_to_samples(self.tick, sr);
        if self.fraction == 0. {
            return left;
        }
        let right = tempo.tick_to_samples(self.tick.saturating_add(1), sr);
        left.saturating_add((right.saturating_sub(left) as f64 * self.fraction).round() as Samples)
    }
}

struct ClipBounds {
    id: ClipId,
    track: usize,
    playlist: usize,
    clip: usize,
    start: Anchor,
    end: Anchor,
}

/// Cached on the host for the lifetime of one immutable score revision. A tempo-only
/// update reuses the same playlist layout and always maps the original boundaries.
#[derive(Default)]
pub struct MidiClipBeatBounds(Vec<ClipBounds>);

impl MidiClipBeatBounds {
    pub fn from_score(score: &Session, include: impl Fn(ClipId) -> bool) -> Self {
        let mut bounds = Vec::new();
        for (track, tr) in score.tracks.iter().enumerate().filter(|(_, tr)| tr.ticks_timebase) {
            for (playlist, pl) in tr.playlists.iter().enumerate() {
                for (clip, c) in pl.clips.iter().enumerate() {
                    // Keep locked clip boundaries at their protected sample positions.
                    if !c.edit_locked && !c.time_locked && matches!(c.content, ClipContent::Midi { .. }) && include(c.id) {
                        bounds.push(ClipBounds {
                            id: c.id,
                            track,
                            playlist,
                            clip,
                            start: Anchor::new(c.start, &score.tempo, score.sample_rate),
                            end: Anchor::new(c.end(), &score.tempo, score.sample_rate),
                        });
                    }
                }
            }
        }
        Self(bounds)
    }

    /// Apply only to clips still present at the cached location.
    pub fn apply(&self, session: &mut Session, tempo: &TempoMap) {
        for b in &self.0 {
            let Some(clip) = session.tracks.get_mut(b.track)
                .and_then(|track| track.playlists.get_mut(b.playlist))
                .and_then(|playlist| playlist.clips.get_mut(b.clip))
                .filter(|clip| clip.id == b.id) else { continue };
            clip.start = b.start.sample(tempo, session.sample_rate);
            clip.length = b.end.sample(tempo, session.sample_rate).saturating_sub(clip.start).max(0);
        }
    }
}
}
use bounds::MidiClipBeatBounds;use soundcraft_model::{Session,Insert,TrackKind,Clip};use soundcraft_model::ChannelFormat;
fn synth_session(level_db: f32) -> Session {
    use soundcraft_midi::{Note, Sequence};
    let mut s = Session::default();
    let t = s.add_track(TrackKind::Instrument, ChannelFormat::Stereo, None);
    let mut seq = Sequence::default();
    seq.notes.push(Note { pitch: 60, velocity: 100, release_velocity: 64, channel: 0, start: 0, length: 960 });
    let cid = s.new_clip_id();
    let tr = s.track_mut(t).unwrap();
    tr.playlist_mut().unwrap().clips.push(Clip::midi(cid, "n", 0, 24_000, seq));
    let mut ins = Insert::new("subtractive_synth");
    ins.params.insert("level".into(), level_db);
    tr.instrument = Some(ins);
    s
}
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
