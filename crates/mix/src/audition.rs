//! Auditioning notes from the Edit window: a key of a track's mini-keyboard sounds on that one
//! track's instrument (Pro Tools Reference Guide p.861: "You can click the mini-keyboard to play
//! pitches using the track's selected MIDI output").
//!
//! An audition note is not live input: it goes to the track it was played on whatever its
//! record-enable, input monitor, MIDI input and Options › MIDI Thru say, and it is never
//! recorded. The audio host fills [`crate::MixEngine::audition`] before a block; the track's
//! mute and solo apply to its audio as for anything else it plays.
//!
//! While stopped, a track that is not playing live input is not rendered. One that auditions is,
//! while it holds an audition note and for [`AUDITION_TAIL_SECONDS`] after the last one ends,
//! so the instrument's release is heard.

use super::LiveMidi;
use soundcraft_dsp::Plugin;
use soundcraft_model::TrackId;

/// How long a track keeps being rendered while stopped after its last audition event.
pub const AUDITION_TAIL_SECONDS: f32 = 2.0;

/// The audition notes a strip holds on its instrument, and how long it keeps rendering.
#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct Audition {
    held: [u64; 2],
    tail: usize,
}

fn bit(note: u8) -> (usize, u64) {
    (usize::from(note >> 6) & 1, 1u64 << (note & 63))
}

impl Audition {
    fn holds(&self, note: u8) -> bool {
        let (w, b) = bit(note);
        self.held.get(w).is_some_and(|x| x & b != 0)
    }

    fn set(&mut self, note: u8, on: bool) {
        let (w, b) = bit(note);
        if let Some(x) = self.held.get_mut(w) {
            if on {
                *x |= b;
            } else {
                *x &= !b;
            }
        }
    }

    /// Whether track `t` has to be rendered while stopped: it holds an audition note, its
    /// instrument is still ringing out, or `events` has one for it.
    pub(crate) fn active(&self, t: TrackId, events: &[(TrackId, LiveMidi)]) -> bool {
        self.held != [0, 0] || self.tail > 0 || events.iter().any(|(id, _)| *id == t)
    }

    /// Play the block's audition events for track `t` on `inst`. A note-off is not sent for a
    /// pitch that `keep` says something else (the clips, live input) still sounds. `tail` is
    /// [`AUDITION_TAIL_SECONDS`] in frames.
    pub(crate) fn play(
        &mut self,
        t: TrackId,
        inst: &mut dyn Plugin,
        events: &[(TrackId, LiveMidi)],
        frames: usize,
        tail: usize,
        keep: impl Fn(u8) -> bool,
    ) {
        let mut any = false;
        for (_, e) in events.iter().filter(|(id, _)| *id == t) {
            any = true;
            let at = usize::try_from(e.offset).unwrap_or(0).min(frames.saturating_sub(1));
            let (kind, note, velocity) = (e.status & 0xF0, e.data1 & 0x7F, e.data2 & 0x7F);
            match kind {
                0x90 if velocity > 0 => {
                    if self.holds(note) {
                        inst.note_off(at, note);
                    }
                    inst.note_on(at, note, velocity);
                    self.set(note, true);
                }
                0x80 | 0x90 if self.holds(note) => {
                    self.set(note, false);
                    if !keep(note) {
                        inst.note_off(at, note);
                    }
                }
                _ => {}
            }
        }
        if any || self.held != [0, 0] {
            self.tail = tail;
        } else {
            self.tail = self.tail.saturating_sub(frames);
        }
    }

    /// Forget the held notes: the instrument was told All Notes Off (a seek).
    pub(crate) fn clear(&mut self) {
        self.held = [0, 0];
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Default)]
    struct Log(Vec<(bool, u8)>);
    impl Plugin for Log {
        fn info(&self) -> &'static soundcraft_dsp::PluginInfo {
            soundcraft_dsp::create("gain").unwrap().info()
        }
        fn prepare(&mut self, _: f32, _: usize, _: usize) {}
        fn reset(&mut self) {}
        fn set_param(&mut self, _: &str, _: f32) -> bool {
            false
        }
        fn param(&self, _: &str) -> Option<f32> {
            None
        }
        fn process(&mut self, _io: &mut [Vec<f32>], _frames: usize) {}
        fn note_on(&mut self, _offset: usize, note: u8, _velocity: u8) {
            self.0.push((true, note));
        }
        fn note_off(&mut self, _offset: usize, note: u8) {
            self.0.push((false, note));
        }
    }

    fn ev(status: u8, note: u8, velocity: u8) -> LiveMidi {
        LiveMidi { offset: 0, port: u8::MAX, status, data1: note, data2: velocity, echo: false }
    }

    #[test]
    fn an_audition_note_plays_only_on_its_track_and_ends_where_it_started() {
        let (a, b) = (TrackId(1), TrackId(2));
        let mut au = Audition::default();
        let mut log = Log::default();
        let events = [(a, ev(0x90, 60, 100)), (b, ev(0x90, 64, 100))];
        au.play(a, &mut log, &events, 512, 1000, |_| false);
        assert_eq!(log.0, [(true, 60)], "the other track's note is not this one's");
        assert!(au.active(a, &[]), "a held note keeps the track rendered");
        // A second strike of the held key ends it first.
        au.play(a, &mut log, &[(a, ev(0x90, 60, 90))], 512, 1000, |_| false);
        assert_eq!(log.0[1..], [(false, 60), (true, 60)]);
        // A note-off the clips still sound is not sent; a key never struck sends nothing.
        au.play(a, &mut log, &[(a, ev(0x80, 60, 0)), (a, ev(0x80, 61, 0))], 512, 1000, |n| n == 60);
        assert_eq!(log.0.len(), 3);
        // The tail runs out block by block once nothing is held.
        assert!(au.active(a, &[]));
        au.play(a, &mut log, &[], 512, 1000, |_| false);
        au.play(a, &mut log, &[], 512, 1000, |_| false);
        assert!(!au.active(a, &[]), "rendered while stopped only until the release has rung out");
    }
}
