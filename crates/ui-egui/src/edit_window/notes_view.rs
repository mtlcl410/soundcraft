//! Notes view of MIDI and instrument tracks: notes on pitch rows, with a mini-keyboard at the
//! left of the playlist (Pro Tools Reference Guide p.861).
//!
//! - The rows show as many pitches as the track height holds; notes above or below them are drawn
//!   as single-pixel lines at the very top and bottom of the range.
//! - The mini-keyboard has octave numbers. Clicking a key plays its pitch on the track (its
//!   instrument and its MIDI output), dragging plays each key passed, and clicking clears the
//!   Edit selection. Arrows at its top and bottom scroll the notes up and down, except at the
//!   smaller track heights.
//! - Where the rows start is kept per track for this run; until a track is scrolled, the rows are
//!   centred on its notes.

use super::layout::lane_rect;
use super::{Align2, Color32, Rect, Sense, SoundApp, Stroke, Tokens, Track, TrackId, Ui, json, pos2, regular, vec2};
use soundcraft_model::ClipContent;

/// Width of the mini-keyboard.
pub(super) const MINI_KEYS_W: f32 = 24.0;
/// Height of each scroll arrow.
const ARROW_H: f32 = 10.0;
/// Below this track height the mini-keyboard has no arrows ("not available in the smaller track
/// heights", p.861): Small and lower.
const ARROWS_MIN_H: f32 = 60.0;
/// Rows per track height: as many as fit at this many points each, within [`MIN_ROW_H`] and
/// [`MAX_ROW_H`].
const ROWS_PER_TRACK: f32 = 24.0;
const MIN_ROW_H: f32 = 3.0;
const MAX_ROW_H: f32 = 8.0;
/// Pressing an arrow scrolls one semitone, then repeats at this interval (seconds) after
/// [`ARROW_DELAY`] while held, like a scroll bar's arrow.
const ARROW_REPEAT: f64 = 0.06;
const ARROW_DELAY: f64 = 0.3;

/// The pitch rows of a track in Notes view.
#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) struct NoteRows {
    /// Where the rows are drawn (the keyboard's keys and the notes share it).
    pub(crate) area: Rect,
    pub(crate) row_h: f32,
    /// The highest pitch shown.
    pub(crate) top: i32,
}

/// Where a note goes in [`NoteRows`].
#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) enum Place {
    /// On its row, from this y.
    Row(f32),
    /// Above the rows shown: a line at the very top.
    Above,
    /// Below: a line at the very bottom.
    Below,
}

impl NoteRows {
    /// The rows in `body` (a track's lane, less the arrows when it has them) from pitch `top` down.
    pub(crate) fn new(body: Rect, top: i32) -> NoteRows {
        let row_h = (body.height() / ROWS_PER_TRACK).clamp(MIN_ROW_H, MAX_ROW_H);
        let rows = Self::fit(body.height(), row_h);
        NoteRows { area: body, row_h, top: top.clamp(rows - 1, 127) }
    }

    fn fit(height: f32, row_h: f32) -> i32 {
        ((height / row_h).floor() as i32).clamp(1, 128)
    }

    /// How many pitches are shown.
    pub(crate) fn rows(&self) -> i32 {
        Self::fit(self.area.height(), self.row_h)
    }

    /// The lowest pitch shown.
    pub(crate) fn bottom(&self) -> i32 {
        self.top - self.rows() + 1
    }

    pub(crate) fn place(&self, pitch: i32) -> Place {
        if pitch > self.top {
            Place::Above
        } else if pitch < self.bottom() {
            Place::Below
        } else {
            Place::Row(self.area.min.y + (self.top - pitch) as f32 * self.row_h)
        }
    }

    /// The pitch of the row at `y`, within those shown.
    pub(crate) fn pitch_at(&self, y: f32) -> i32 {
        (self.top - ((y - self.area.min.y) / self.row_h).floor() as i32).clamp(self.bottom(), self.top)
    }
}

/// Whether a track of this height shows the scroll arrows.
fn has_arrows(lane: Rect) -> bool {
    lane.height() >= ARROWS_MIN_H
}

/// Whether `track` is in Notes view (MIDI and instrument tracks).
pub(super) fn in_notes_view(track: &Track) -> bool {
    track.kind.is_midi() && track.view == "notes"
}

/// The highest pitch to show for `track` by default: its notes centred in `rows` rows (middle C
/// when it has none).
fn centred_top(track: &Track, rows: i32) -> i32 {
    let (lo, hi) = track
        .clips()
        .iter()
        .filter_map(|c| match &c.content {
            ClipContent::Midi { sequence } => Some(sequence.notes.iter().map(|n| i32::from(n.pitch))),
            _ => None,
        })
        .flatten()
        .fold((i32::MAX, i32::MIN), |(lo, hi), p| (lo.min(p), hi.max(p)));
    let middle = if lo > hi { 60 } else { (lo + hi) / 2 };
    middle + rows / 2
}

/// The pitch rows of `track` in its lane `lane`.
pub(crate) fn note_rows(app: &SoundApp, track: &Track, lane: Rect) -> NoteRows {
    let body = Rect::from_min_max(pos2(lane.min.x, lane.min.y + 1.0), pos2(lane.max.x, lane.max.y - 1.0));
    let body =
        if has_arrows(lane) { Rect::from_min_max(pos2(body.min.x, body.min.y + ARROW_H), pos2(body.max.x, body.max.y - ARROW_H)) } else { body };
    let probe = NoteRows::new(body, 127);
    let top = app.edit_layout.notes_top.get(&track.id).copied().unwrap_or_else(|| centred_top(track, probe.rows()));
    NoteRows::new(body, top)
}

/// Scroll `track`'s notes by `semitones` (up is positive).
fn scroll(app: &mut SoundApp, id: TrackId, rows: &NoteRows, semitones: i32) {
    let top = (rows.top + semitones).clamp(rows.rows() - 1, 127);
    app.edit_layout.notes_top.insert(id, top);
}

/// Draw the mini-keyboard of `track` (in Notes view) and handle its keys and arrows. Called after
/// the lane's own interaction, so it takes the pointer over the keyboard.
pub(super) fn mini_keyboard(app: &mut SoundApp, ui: &mut Ui, track: &Track, row: Rect, tl: Rect) {
    let lane = lane_rect(track, row, tl);
    if !in_notes_view(track) || lane.height() < 8.0 || !ui.is_rect_visible(lane) {
        return;
    }
    let t = Tokens::current();
    let rows = note_rows(app, track, lane);
    let x0 = lane.min.x;
    let keys = Rect::from_min_max(pos2(x0, rows.area.min.y), pos2(x0 + MINI_KEYS_W, rows.area.min.y + rows.rows() as f32 * rows.row_h));
    let painter = ui.painter().with_clip_rect(lane.intersect(ui.clip_rect()));
    painter.rect_filled(Rect::from_min_max(pos2(x0, lane.min.y), pos2(x0 + MINI_KEYS_W, lane.max.y)), 0.0, t.panel_bg2);
    let held = app.auditioning().filter(|(id, _)| *id == track.id).map(|(_, p)| i32::from(p));
    for pitch in rows.bottom()..=rows.top {
        let Place::Row(y) = rows.place(pitch) else { continue };
        let black = matches!(pitch.rem_euclid(12), 1 | 3 | 6 | 8 | 10);
        let key = Rect::from_min_size(pos2(x0, y), vec2(if black { MINI_KEYS_W * 0.6 } else { MINI_KEYS_W - 1.0 }, rows.row_h - 0.5));
        let fill = if held == Some(pitch) {
            t.accent
        } else if black {
            Color32::from_rgb(24, 24, 24)
        } else {
            Color32::from_rgb(222, 222, 222)
        };
        painter.rect_filled(key, 0.5, fill);
        if pitch.rem_euclid(12) == 0 {
            painter.line_segment(
                [pos2(x0, y + rows.row_h - 0.5), pos2(x0 + MINI_KEYS_W, y + rows.row_h - 0.5)],
                Stroke::new(1.0, Color32::from_rgb(90, 90, 90)),
            );
            painter.text(
                pos2(x0 + MINI_KEYS_W - 2.0, y + rows.row_h),
                Align2::RIGHT_BOTTOM,
                soundcraft_midi::note_name(pitch as u8),
                regular(7.5),
                Color32::from_rgb(40, 40, 40),
            );
        }
    }
    painter.vline(x0 + MINI_KEYS_W, lane.y_range(), Stroke::new(1.0, t.border));
    let resp = ui.interact(keys, ui.scope_id().with(("mini_keyboard", track.id.0)), Sense::click_and_drag());
    let name = crate::localized_format!("Mini-keyboard of {name}", name = track.name.as_str());
    resp.widget_info(|| egui::WidgetInfo::labeled(egui::Role::Button, true, name.as_str()));
    if (resp.is_pointer_button_down_on() || resp.clicked())
        && let Some(p) = resp.interact_pointer_pos()
    {
        let pitch = rows.pitch_at(p.y);
        app.audition_hold(track.id, pitch as u8, crate::midi_editor::KEY_VELOCITY);
        // "Clicking the mini-keyboard clears the current Edit selection" (p.861).
        if ui.input(|i| i.pointer.primary_pressed()) {
            let start = app.engine.session().edit.selection.start;
            let _ = app.run("edit.select", json!({"start": start, "clips": []}));
        }
    }
    if has_arrows(lane) {
        let now = ui.input(|i| i.time);
        for (up, r) in [
            (true, Rect::from_min_max(pos2(x0, lane.min.y + 1.0), pos2(x0 + MINI_KEYS_W, lane.min.y + 1.0 + ARROW_H))),
            (false, Rect::from_min_max(pos2(x0, lane.max.y - 1.0 - ARROW_H), pos2(x0 + MINI_KEYS_W, lane.max.y - 1.0))),
        ] {
            let resp = ui.interact(r, ui.scope_id().with(("notes_arrow", track.id.0, up)), Sense::click_and_drag());
            let name = track.name.as_str();
            let label = if up {
                crate::localized_format!("Scroll notes of {name} up", name = name)
            } else {
                crate::localized_format!("Scroll notes of {name} down", name = name)
            };
            resp.widget_info(|| egui::WidgetInfo::labeled(egui::Role::Button, true, label.as_str()));
            let ink = if resp.hovered() { t.text } else { t.text_dim };
            let (c, h) = (r.center(), ARROW_H * 0.3);
            let tip = if up { c.y - h } else { c.y + h };
            let base = if up { c.y + h } else { c.y - h };
            painter.add(egui::Shape::convex_polygon(vec![pos2(c.x, tip), pos2(c.x - h * 1.6, base), pos2(c.x + h * 1.6, base)], ink, Stroke::NONE));
            let step = if up { 1 } else { -1 };
            if resp.is_pointer_button_down_on() || resp.clicked() {
                match app.edit_layout.notes_arrow_at {
                    // The press: one semitone at once, then again while held.
                    None => {
                        scroll(app, track.id, &rows, step);
                        app.edit_layout.notes_arrow_at = Some(now + ARROW_DELAY);
                    }
                    Some(at) if now >= at && !resp.clicked() => {
                        scroll(app, track.id, &rows, step);
                        app.edit_layout.notes_arrow_at = Some(now + ARROW_REPEAT);
                    }
                    Some(_) => {}
                }
                ui.ctx().request_repaint_after(std::time::Duration::from_secs_f64(ARROW_REPEAT));
            }
        }
        if !ui.input(|i| i.pointer.primary_down()) {
            app.edit_layout.notes_arrow_at = None;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rows_fill_the_track_and_notes_outside_them_go_to_the_edges() {
        let body = Rect::from_min_max(pos2(0.0, 0.0), pos2(100.0, 96.0));
        let rows = NoteRows::new(body, 72);
        assert_eq!(rows.row_h * rows.rows() as f32, 96.0, "the rows fill the lane");
        assert_eq!(rows.place(72), Place::Row(0.0));
        assert_eq!(rows.place(rows.bottom()), Place::Row(96.0 - rows.row_h));
        assert_eq!(rows.place(73), Place::Above);
        assert_eq!(rows.place(rows.bottom() - 1), Place::Below);
        assert_eq!(rows.pitch_at(1.0), 72);
        assert_eq!(rows.pitch_at(95.0), rows.bottom());
        // A taller track shows more pitches.
        let tall = NoteRows::new(Rect::from_min_max(pos2(0.0, 0.0), pos2(100.0, 400.0)), 72);
        assert!(tall.rows() > rows.rows());
        // The top cannot leave the MIDI range.
        assert_eq!(NoteRows::new(body, 500).top, 127);
        assert_eq!(NoteRows::new(body, -5).bottom(), 0);
    }
}
