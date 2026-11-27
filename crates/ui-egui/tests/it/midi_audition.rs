//! Auditioning from the editors (Pro Tools Reference Guide p.861, p.1022, p.1030, p.1074): the
//! Edit window's mini-keyboard and the MIDI Editor's keyboard play a key on their track while it
//! is held, and Play MIDI Notes When Editing (on by default) plays the notes inserted or clicked.
//! What is played reaches the MIDI feed's audition path ([`MidiFeed::auditioned`]), which sends
//! it to that track only and never records it.
use egui::{Event, Modifiers, PointerButton, Pos2, Rect, pos2, vec2};
use egui_kittest::Harness;
use egui_kittest::kittest::Queryable;
use serde_json::json;
use soundcraft_model::TrackId;
use soundcraft_playback::midi::MidiInputs;
use soundcraft_ui_egui::{Services, SoundApp};

fn harness(midi_editor: bool) -> Harness<'static, SoundApp> {
    let mut app = SoundApp::new(soundcraft_engine::demo::demo_engine(), None, Services::default());
    app.midi_inputs = Some(MidiInputs::with_port_names(Vec::new(), Vec::new()));
    app.ui.show_midi_editor = midi_editor;
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
    let mut h = harness(false);
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
    let mut h = harness(false);
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

#[test]
fn the_midi_editor_keyboard_plays_and_selects_the_notes_of_its_pitch() {
    let mut h = harness(true);
    let keys = keys_track(&h);
    let strip = rect_of(&h, "MIDI Editor keyboard");
    // Some key with notes on it: the editor opens centred on the clip's notes.
    let at = pos2(strip.center().x, strip.center().y);
    pointer(&mut h, at, Some(true), Modifiers::NONE);
    let (_, e) = last(&h);
    let (track, status, pitch) = e.expect("the key plays");
    assert_eq!((track, status), (keys, 0x90));
    let notes = {
        let s = h.state().engine.session();
        let cid = soundcraft_ui_egui::midi_editor::target_clip(h.state()).unwrap();
        match &s.find_clip(cid).unwrap().1.content {
            soundcraft_model::ClipContent::Midi { sequence } => sequence.notes.clone(),
            _ => unreachable!(),
        }
    };
    let of_pitch: Vec<usize> = notes.iter().enumerate().filter(|(_, n)| n.pitch == pitch).map(|(i, _)| i).collect();
    assert_eq!(h.state().midi.selected, of_pitch, "the notes of that pitch are selected");
    pointer(&mut h, at, Some(false), Modifiers::NONE);
    // Alt plays without selecting.
    h.state_mut().midi.selected.clear();
    pointer(&mut h, at, Some(true), Modifiers::ALT);
    pointer(&mut h, at, Some(false), Modifiers::ALT);
    assert!(h.state().midi.selected.is_empty());
    // Closing the editor while a key is held lets go of it.
    pointer(&mut h, at, Some(true), Modifiers::NONE);
    let n = last(&h).0;
    h.state_mut().ui.show_midi_editor = false;
    std::thread::sleep(std::time::Duration::from_millis(300));
    h.run_steps(3);
    assert_eq!(last(&h), (n + 1, Some((keys, 0x80, pitch))));
}

#[test]
fn play_midi_notes_when_editing_plays_an_inserted_note_and_is_on_by_default() {
    let mut h = harness(true);
    let keys = keys_track(&h);
    h.state_mut().run("edit.tool", json!({"tool": "pencil"})).unwrap();
    h.run_steps(2);
    let roll = rect_of(&h, "Piano roll");
    // An empty spot: the top of the roll is far above the clip's notes.
    let at = pos2(roll.right() - 6.0, roll.top() + 4.0);
    pointer(&mut h, at, Some(true), Modifiers::NONE);
    pointer(&mut h, at, Some(false), Modifiers::NONE);
    let (n, e) = last(&h);
    assert!(n >= 1 && e.is_some_and(|(t, s, _)| t == keys && s == 0x90), "the inserted note sounds: {n} {e:?}");
    // Switched off with the toolbar button: inserting is silent.
    h.get_all_by_label("Play MIDI Notes When Editing").last().unwrap().click();
    h.run_steps(2);
    assert!(!soundcraft_engine::cmd::play_midi_notes_when_editing(h.state().engine.session()));
    std::thread::sleep(std::time::Duration::from_millis(300));
    h.run_steps(3);
    let n = last(&h).0;
    let at = pos2(roll.right() - 30.0, roll.top() + 4.0);
    pointer(&mut h, at, Some(true), Modifiers::NONE);
    pointer(&mut h, at, Some(false), Modifiers::NONE);
    assert_eq!(last(&h).0, n, "nothing is played with the option off");
}
