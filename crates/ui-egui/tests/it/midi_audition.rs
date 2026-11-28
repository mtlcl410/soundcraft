//! Auditioning from the Edit window (Pro Tools Reference Guide p.861): a key of a track's
//! mini-keyboard in Notes view plays on that track while it is held.
//! What is played reaches the MIDI feed's audition path ([`MidiFeed::auditioned`]), which sends
//! it to that track only and never records it.
use egui::{Event, Modifiers, PointerButton, Pos2, Rect, pos2, vec2};
use egui_kittest::Harness;
use egui_kittest::kittest::Queryable;
use serde_json::json;
use soundcraft_model::TrackId;
use soundcraft_playback::midi::MidiInputs;
use soundcraft_ui_egui::{Services, SoundApp};

fn harness() -> Harness<'static, SoundApp> {
    let mut app = SoundApp::new(soundcraft_engine::demo::demo_engine(), None, Services::default());
    app.midi_inputs = Some(MidiInputs::with_port_names(Vec::new(), Vec::new()));
    app.run("edit.select", json!({"tracks": ["Keys"]})).unwrap();
    let mut h = Harness::builder()
        .with_context_setup(soundcraft_ui_egui::framework::install_headless)
        .with_size(vec2(1600.0, 1200.0))
        .with_pixels_per_point(1.0)
        .build_ui_state(
            |ui, app: &mut SoundApp| {
                let ctx = ui.ctx().clone();
                app.logic(&ctx);
                app.ui(ui);
            },
            app,
        );
    h.run_steps(4);
    h
}

fn keys_track(h: &Harness<'_, SoundApp>) -> TrackId {
    h.state().engine.session().track_by_name("Keys").unwrap().id
}

fn pointer(h: &mut Harness<'_, SoundApp>, pos: Pos2, pressed: Option<bool>, modifiers: Modifiers) {
    h.input_mut().events.push(Event::ModifiersChanged(modifiers));
    h.input_mut().events.push(Event::PointerMoved(pos));
    if let Some(pressed) = pressed {
        h.input_mut().events.push(Event::PointerButton { pos, button: PointerButton::Primary, pressed, modifiers });
    }
    h.run_steps(2);
}

/// Audition events so far, and the last one (track, status, key).
fn last(h: &Harness<'_, SoundApp>) -> (u32, Option<(TrackId, u8, u8)>) {
    let (n, e) = h.state().midi_inputs.as_ref().unwrap().feed().auditioned();
    (n, e.map(|(t, b)| (t, b[0] & 0xF0, b[1])))
}

fn rect_of(h: &Harness<'_, SoundApp>, label: &str) -> Rect {
    h.get_by_label(label).rect()
}

#[test]
fn a_mini_keyboard_key_plays_its_track_while_held_and_clears_the_edit_selection() {
    let mut h = harness();
    let keys = keys_track(&h);
    h.state_mut().run("edit.select", json!({"tracks": ["Keys"], "start": 48_000, "end": 96_000})).unwrap();
    h.run_steps(2);
    let kb = rect_of(&h, "Mini-keyboard of Keys");
    let at = pos2(kb.left() + 4.0, kb.center().y);
    pointer(&mut h, at, None, Modifiers::NONE);
    assert_eq!(last(&h).0, 0, "hovering plays nothing");
    pointer(&mut h, at, Some(true), Modifiers::NONE);
    let (n, e) = last(&h);
    let (track, status, pitch) = e.expect("the key plays");
    assert_eq!((n, track, status), (1, keys, 0x90));
    assert!(h.state().engine.session().edit.selection.is_empty(), "clicking the mini-keyboard clears the Edit selection");
    pointer(&mut h, at, None, Modifiers::NONE);
    assert_eq!(last(&h).0, 1, "held: nothing more");
    // Dragging up plays the higher key, ending the first before it.
    pointer(&mut h, pos2(at.x, kb.top() + 2.0), None, Modifiers::NONE);
    let (n, e) = last(&h);
    assert!(n == 3 && e.is_some_and(|(_, s, p)| s == 0x90 && p > pitch), "{n} {e:?}");
    let higher = e.unwrap().2;
    pointer(&mut h, pos2(at.x, kb.top() + 2.0), Some(false), Modifiers::NONE);
    // The note sounds a quarter second at least, then ends.
    std::thread::sleep(std::time::Duration::from_millis(300));
    h.run_steps(3);
    assert_eq!(last(&h), (4, Some((keys, 0x80, higher))));
}

#[test]
fn the_arrows_scroll_the_notes_and_are_not_there_at_small_heights() {
    let mut h = harness();
    let kb = rect_of(&h, "Mini-keyboard of Keys");
    let pitch_at = |h: &mut Harness<'_, SoundApp>| {
        let at = pos2(kb.left() + 4.0, kb.center().y);
        pointer(h, at, Some(true), Modifiers::NONE);
        pointer(h, at, Some(false), Modifiers::NONE);
        last(h).1.unwrap().2
    };
    let before = pitch_at(&mut h);
    let up = rect_of(&h, "Scroll notes of Keys up").center();
    pointer(&mut h, up, Some(true), Modifiers::NONE);
    pointer(&mut h, up, Some(false), Modifiers::NONE);
    assert_eq!(pitch_at(&mut h), before + 1, "one semitone up");
    let down = rect_of(&h, "Scroll notes of Keys down").center();
    for _ in 0..3 {
        pointer(&mut h, down, Some(true), Modifiers::NONE);
        pointer(&mut h, down, Some(false), Modifiers::NONE);
    }
    assert_eq!(pitch_at(&mut h), before - 2);
    h.state_mut().run("track.height", json!({"tracks": ["Keys"], "height": "small"})).unwrap();
    h.run_steps(2);
    assert!(h.query_by_label("Mini-keyboard of Keys").is_some(), "the keyboard stays");
    assert!(h.query_by_label("Scroll notes of Keys up").is_none(), "no arrows at a small height");
}
