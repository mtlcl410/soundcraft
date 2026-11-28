//! Wait for Note (Pro Tools Reference Guide p. 812–813): in Record Ready, the record pass starts
//! with the first MIDI event played, in place of Play (p. 818 step 5, p. 828 step 8), and that
//! event is at the start point.
//!
//! The MIDI feed notes when that event arrives, on its device thread ([`MidiFeed::wait_for_event`]);
//! this frame loop then starts the pass through [`SoundApp::start_recording`], the one place a
//! pass starts. The pass begins from the event's arrival, and the audio engine places the
//! playhead by it ([`soundcraft_playback::Player::play_from_event`]), so the event and what was
//! played after it keep their places however long the frame took.

use super::{Samples, SoundApp};
use soundcraft_engine::WAIT_FOR_NOTE;
use soundcraft_model::MidiInput;
use soundcraft_playback::midi::MidiFeed;
use std::sync::Arc;

/// The status line while waiting.
const WAITING: &str = "Wait for Note: recording starts with the first MIDI event you play. Stop or Record again cancels.";
/// Record Ready with Wait for Note on, and nothing it could wait for.
const AUDIO_ONLY: &str =
    "Record Ready: Wait for Note waits only for MIDI, and no MIDI or instrument track is record-enabled. Press Play or Space to record.";

impl SoundApp {
    /// Whether Wait for Note is on (`options.wait_for_note`, saved with the session).
    pub fn wait_for_note(&self) -> bool {
        self.engine.session().edit.flag(WAIT_FOR_NOTE)
    }

    /// Whether a record pass from stop waits for a MIDI event: Wait for Note is on and a MIDI or
    /// instrument track is record-enabled. With only audio tracks there is nothing to wait for:
    /// the pass starts as without it.
    pub(crate) fn pass_waits_for_note(&self) -> bool {
        self.wait_for_note() && soundcraft_engine::io::records_midi(&self.engine)
    }

    /// Record Ready, waiting for the MIDI event that starts the pass. Record, Play and Wait for
    /// Note flash (p. 828 step 8).
    pub fn waiting_for_note(&self) -> bool {
        self.record_ready() && self.pass_waits_for_note()
    }

    /// Every frame: while waiting, tell the MIDI feed which inputs count and start the pass
    /// once one of them has sent an event. A wait that no input could end is cancelled with the
    /// reason, never left to wait in silence.
    pub(crate) fn service_wait_for_note(&mut self, ctx: &egui::Context) {
        let waiting = self.waiting_for_note();
        let was = std::mem::replace(&mut self.note_wait, waiting);
        self.engine.transport.waiting_for_note = waiting;
        let feed = self.midi_inputs.as_ref().map(|m| Arc::clone(m.feed()));
        if !waiting {
            if was {
                if let Some(feed) = &feed {
                    feed.stop_waiting();
                }
                if self.ui.status == crate::localization::text(WAITING) {
                    self.ui.status.clear();
                }
            }
            if self.record_ready() && self.wait_for_note() && self.ui.status == crate::localization::text(super::playback::RECORD_READY) {
                self.ui.status = crate::localization::text(AUDIO_ONLY).into();
            }
            return;
        }
        let inputs = feed.as_ref().map(|f| (self.note_inputs(f), f));
        let Some((Some((ports, kinds)), feed)) = inputs else {
            self.note_wait = false;
            self.engine.transport.waiting_for_note = false;
            self.leave_record_ready();
            if let Some(feed) = &feed {
                feed.stop_waiting();
            }
            self.ui.status = if was {
                crate::localization::text(
                    "Wait for Note cancelled: no connected MIDI input device is one that a record-enabled track listens to (Setup > Playback Engine lists them).",
                )
            } else {
                crate::localization::text(
                    "Cannot wait for a note: no connected MIDI input device is one that a record-enabled track listens to (Setup > Playback Engine lists them).",
                )
            }
            .into();
            return;
        };
        feed.wait_for_event(ports, kinds);
        if !was {
            self.ui.status = crate::localization::text(WAITING).into();
        }
        match feed.waited_event() {
            Some(at) => self.start_on_note(Arc::clone(feed), at),
            // The event is noticed on the next frame: keep them coming while waiting.
            None => ctx.request_repaint_after_secs(0.005),
        }
    }

    /// The inputs whose events start the pass: for each channel, the open ports
    /// ([`soundcraft_mix::midi_port_bit`]) a record-enabled MIDI or instrument track takes it from,
    /// and the kinds of message the MIDI Input Filter lets into the take. `None` when no open
    /// port is one of them.
    fn note_inputs(&self, feed: &MidiFeed) -> Option<([u64; 16], u32)> {
        let open: Vec<(String, u8)> =
            self.midi_inputs.as_ref()?.ports().iter().filter(|p| p.open).map(|p| (p.name.clone(), feed.ports().assign(&p.name))).collect();
        let mut ports = [0u64; 16];
        for (_, route) in soundcraft_engine::io::midi_record_inputs(&self.engine) {
            let input = MidiInput::of(&route);
            for (name, port) in &open {
                for (channel, mask) in (0u8..).zip(ports.iter_mut()) {
                    if input.accepts(Some(name), channel) {
                        *mask |= soundcraft_mix::midi_port_bit(*port);
                    }
                }
            }
        }
        let s = self.engine.session();
        let kinds = (0x9u8..=0xE).filter(|k| !soundcraft_engine::io::midi_filtered(s, k << 4)).fold(0u32, |m, k| m | 1 << (k & 7));
        (kinds != 0 && ports.iter().any(|p| *p != 0)).then_some((ports, kinds))
    }

    /// The event that arrived at `at` starts the pass, as Play would (p. 818 step 5), without
    /// the pre-roll (p. 812: "Wait for Note starts recording immediately, ignoring any specified
    /// Pre-roll").
    fn start_on_note(&mut self, feed: Arc<MidiFeed>, at: i64) {
        self.note_start = Some(at);
        self.start_recording(None);
        self.note_start = None;
        // The audio engine holds what came since `at` by the start of the pass from here on.
        feed.stop_waiting();
        self.note_wait = false;
        self.engine.transport.waiting_for_note = false;
        if !self.engine.transport.recording {
            // `start_recording` said why.
            return;
        }
        if self.ui.status == crate::localization::text(WAITING) {
            self.ui.status.clear();
        }
        // The audio input records from now, which is this far past the start point on the
        // playhead: the audio takes go there (a loop pass keeps the loop's own layout).
        let since = self.engine.session().sample_rate.samples(feed.now_micros().saturating_sub(at).max(0) as f64 / 1e6);
        if let Some(plan) = &mut self.take_plan
            && plan.pass.is_none()
            && !plan.takes.is_empty()
        {
            plan.start = plan.start.saturating_add(since.max(0) as Samples);
        }
    }
}
