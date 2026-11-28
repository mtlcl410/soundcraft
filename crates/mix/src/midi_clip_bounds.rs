//! Preserve the musical start and exclusive end of MIDI clips across tempo-map changes.
use soundcraft_model::{ClipContent, ClipId, Session};
use soundcraft_time::{SampleRate, Samples, TempoMap};

#[derive(Clone, Copy)]
struct Anchor {
    tick: i64,
    /// Position inside the tick as `offset / span` samples of the original tempo.
    offset: Samples,
    span: Samples,
}

impl Anchor {
    fn new(sample: Samples, tempo: &TempoMap, sr: SampleRate) -> Self {
        let nearest = tempo.samples_to_ticks(sample, sr);
        let at = tempo.tick_to_samples(nearest, sr);
        if sample == at {
            return Self { tick: nearest, offset: 0, span: 1 };
        }
        // Preserve sub-tick trims, including the distinction between a note exactly
        // at the excluded end and one a sample before it.
        let tick = if sample < at { nearest.saturating_sub(1) } else { nearest };
        let left = tempo.tick_to_samples(tick, sr);
        let right = tempo.tick_to_samples(tick.saturating_add(1), sr);
        Self { tick, offset: sample.saturating_sub(left), span: right.saturating_sub(left).max(1) }
    }

    /// A position inside a tick maps to the next sample at or after its scaled offset, so
    /// it stays strictly after the tick it follows: an exclusive end keeps that tick's
    /// attack, and a start keeps it out. A position exactly on a tick stays exact.
    fn sample(self, tempo: &TempoMap, sr: SampleRate) -> Samples {
        let left = tempo.tick_to_samples(self.tick, sr);
        if self.offset == 0 {
            return left;
        }
        let right = tempo.tick_to_samples(self.tick.saturating_add(1), sr);
        let scaled = i128::from(right.saturating_sub(left)) * i128::from(self.offset);
        let span = i128::from(self.span);
        let step = Samples::try_from((scaled + span - 1).div_euclid(span)).unwrap_or(Samples::MAX);
        left.saturating_add(step)
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
            let Some(clip) = session
                .tracks
                .get_mut(b.track)
                .and_then(|track| track.playlists.get_mut(b.playlist))
                .and_then(|playlist| playlist.clips.get_mut(b.clip))
                .filter(|clip| clip.id == b.id)
            else {
                continue;
            };
            clip.start = b.start.sample(tempo, session.sample_rate);
            clip.length = b.end.sample(tempo, session.sample_rate).saturating_sub(clip.start).max(0);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_fractional_end_keeps_an_included_attack_inside_the_clip_at_a_faster_tempo() {
        let sr = SampleRate::HZ_48000;
        let slow = TempoMap::new(120., 4, 4).unwrap();
        let fast = TempoMap::new(300., 4, 4).unwrap();
        // The clip ends one sample after tick 960, so an attack on tick 960 is inside it.
        assert_eq!(slow.tick_to_samples(960, sr), 24_000);
        let end = Anchor::new(24_001, &slow, sr);
        assert!(end.sample(&fast, sr) > fast.tick_to_samples(960, sr));
        // The same fraction at the start keeps that attack outside the clip.
        assert!(Anchor::new(24_001, &slow, sr).sample(&fast, sr) <= fast.tick_to_samples(961, sr));
        // An end exactly on a tick still excludes the attack on that tick.
        assert_eq!(Anchor::new(24_000, &slow, sr).sample(&fast, sr), fast.tick_to_samples(960, sr));
    }

    #[test]
    fn an_unchanged_tempo_maps_every_boundary_back_to_its_sample() {
        let sr = SampleRate::HZ_48000;
        for tempo in [TempoMap::new(120., 4, 4).unwrap(), TempoMap::new(97.3, 4, 4).unwrap()] {
            for sample in 0..5_000 {
                assert_eq!(Anchor::new(sample, &tempo, sr).sample(&tempo, sr), sample);
            }
        }
    }
}
