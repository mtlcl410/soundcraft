//! Window › MIDI Keyboard plays notes from the computer keyboard (#1209, Pro Tools Reference Guide
//! p.827–828): A plays C and T plays F#/Gb, Z/X move the octave and C/V the velocity. While its
//! Computer Keyboard switch is on, those keys play instead of running shortcuts; a note ends when
//! its key comes up, when the switch goes off, when the window closes and when the app loses focus.
use egui::{Event, Key, Modifiers, vec2};
use egui_kittest::{
    Harness,
    kittest::{NodeT, Queryable},
};
use serde_json::json;
use soundcraft_playback::midi::MidiInputs;
use soundcraft_ui_egui::{Services, SoundApp};

type AppHarness = Harness<'static, SoundApp>;

/// The app with no MIDI device and the MIDI Keyboard window open.
fn harness() -> AppHarness {
    let mut app = SoundApp::new(soundcraft_engine::Engine::default(), None, Services::default());
    app.midi_inputs = Some(MidiInputs::with_port_names(Vec::new(), Vec::new()));
    app.ui.show_midi_keyboard = true;
    let mut h =
        Harness::builder().with_context_setup(soundcraft_ui_egui::framework::install_headless).with_size(vec2(1600.0, 1000.0)).build_ui_state(
            |ui, app: &mut SoundApp| {
                app.logic(&ui.ctx().clone());
                app.ui(ui);
            },
            app,
        );
    h.run_steps(3);
    h
}

fn key(h: &mut AppHarness, key: Key, pressed: bool, modifiers: Modifiers) {
    h.event(Event::Key { key, physical_key: None, pressed, repeat: false, modifiers });
    h.run_steps(2);
}

fn down(h: &mut AppHarness, k: Key) {
    key(h, k, true, Modifiers::NONE);
}

fn up(h: &mut AppHarness, k: Key) {
    key(h, k, false, Modifiers::NONE);
}

fn tap(h: &mut AppHarness, k: Key) {
    down(h, k);
    up(h, k);
}

/// (messages so far, status nibble, note, velocity) of the last message the window sent.
fn last(h: &AppHarness) -> (u32, u8, u8, u8) {
    let (count, last) = h.state().midi_inputs.as_ref().unwrap().feed().activity();
    last.map_or((count, 0, 0, 0), |m| (count, m.status & 0xF0, m.data1, m.data2))
}

#[test]
fn computer_keys_play_notes_until_the_key_comes_up() {
    let mut h = harness();
    down(&mut h, Key::A);
    let (count, status, a, velocity) = last(&h);
    assert_eq!((count, status), (1, 0x90), "A plays a note");
    assert!(velocity > 0, "with a velocity");
    assert_eq!(a % 12, 0, "A plays a C");
    up(&mut h, Key::A);
    assert_eq!(last(&h), (2, 0x80, a, 0), "letting go of A ends it");
    down(&mut h, Key::T);
    let (_, status, t, _) = last(&h);
    assert_eq!((status, t), (0x90, a + 6), "T plays the F#/Gb above");
    // A held key's auto-repeat plays nothing more.
    h.event(Event::Key { key: Key::T, physical_key: None, pressed: true, repeat: true, modifiers: Modifiers::NONE });
    h.run_steps(2);
    assert_eq!(last(&h).0, 3, "an auto-repeat is not a new note");
    up(&mut h, Key::T);
    assert_eq!(last(&h), (4, 0x80, t, 0));
}

#[test]
fn z_and_x_move_the_octave_and_c_and_v_the_velocity() {
    let mut h = harness();
    down(&mut h, Key::A);
    let (_, _, c, velocity) = last(&h);
    up(&mut h, Key::A);
    tap(&mut h, Key::X);
    down(&mut h, Key::A);
    assert_eq!(last(&h).2, c + 12, "X moves an octave up");
    // A note held across an octave change ends on the pitch it started on.
    tap(&mut h, Key::Z);
    tap(&mut h, Key::Z);
    up(&mut h, Key::A);
    let (_, status, note, _) = last(&h);
    assert_eq!((status, note), (0x80, c + 12), "the held note ends where it started");
    down(&mut h, Key::A);
    assert_eq!(last(&h).2, c - 12, "Z moves an octave down");
    up(&mut h, Key::A);
    tap(&mut h, Key::V);
    down(&mut h, Key::A);
    let louder = last(&h).3;
    up(&mut h, Key::A);
    assert!(louder > velocity, "V raises the velocity");
    tap(&mut h, Key::C);
    tap(&mut h, Key::C);
    down(&mut h, Key::A);
    assert!(last(&h).3 < velocity, "C lowers it");
    up(&mut h, Key::A);
    // The octave stops at C-2: more Z presses do not wrap or go below note 0.
    for _ in 0..12 {
        tap(&mut h, Key::Z);
    }
    down(&mut h, Key::A);
    assert_eq!(last(&h).2, 0, "the lowest octave starts at C-2");
}

#[test]
fn computer_keys_take_the_place_of_single_key_shortcuts_until_switched_off() {
    let mut h = harness();
    let zoom = |h: &AppHarness| h.state().engine.session().edit.zoom.samples_per_px;
    let before = zoom(&h);
    tap(&mut h, Key::T);
    assert_eq!(zoom(&h), before, "T plays, it does not zoom in");
    // Commands Keyboard Focus's Z is Undo: with the window's keys on it moves the octave instead.
    h.state_mut().run("options.keyboard_focus", json!({"focus": "commands"})).unwrap();
    h.state_mut().run("track.new", json!({"kind": "audio"})).unwrap();
    let tracks = |h: &AppHarness| h.state().engine.session().tracks.len();
    let made = tracks(&h);
    tap(&mut h, Key::Z);
    assert_eq!(tracks(&h), made, "Z did not undo");
    // Shift+K still closes and opens the window.
    key(&mut h, Key::K, true, Modifiers::SHIFT);
    key(&mut h, Key::K, false, Modifiers::SHIFT);
    assert!(!h.state().ui.show_midi_keyboard, "Shift+K closed the window");
    key(&mut h, Key::K, true, Modifiers::SHIFT);
    key(&mut h, Key::K, false, Modifiers::SHIFT);
    assert!(h.state().ui.show_midi_keyboard, "Shift+K opened it again");
    // The switch is shown and hands the keys back to the shortcuts.
    h.get_by_label("Computer Keyboard").click();
    h.run_steps(2);
    assert!(!h.state().ui.midi_keyboard_computer_keys, "switched off");
    let sent = last(&h).0;
    tap(&mut h, Key::T);
    assert!(zoom(&h) < before, "T zooms in again");
    assert_eq!(last(&h).0, sent, "and plays nothing");
    tap(&mut h, Key::Z);
    assert!(tracks(&h) < made, "Z undoes again");
}

#[test]
fn held_keys_end_when_switched_off_when_the_window_closes_and_when_focus_is_lost() {
    let mut h = harness();
    down(&mut h, Key::A);
    let (_, _, a, _) = last(&h);
    h.get_by_label("Computer Keyboard").click();
    h.run_steps(2);
    assert_eq!(last(&h), (2, 0x80, a, 0), "switching off lets go");
    up(&mut h, Key::A);
    assert_eq!(last(&h).0, 2, "the key coming up later sends nothing more");
    h.get_by_label("Computer Keyboard").click();
    h.run_steps(2);
    down(&mut h, Key::A);
    key(&mut h, Key::K, true, Modifiers::SHIFT);
    assert!(!h.state().ui.show_midi_keyboard);
    assert_eq!(last(&h), (4, 0x80, a, 0), "closing the window lets go");
    key(&mut h, Key::K, false, Modifiers::SHIFT);
    up(&mut h, Key::A);
    assert_eq!(last(&h).0, 4, "the key coming up later sends nothing more");
    key(&mut h, Key::K, true, Modifiers::SHIFT);
    key(&mut h, Key::K, false, Modifiers::SHIFT);
    down(&mut h, Key::A);
    assert_eq!(last(&h).0, 5);
    h.input_mut().focused = false;
    h.run_steps(2);
    assert_eq!(last(&h), (6, 0x80, a, 0), "losing focus lets go");
    h.input_mut().focused = true;
    up(&mut h, Key::A);
    assert_eq!(last(&h).0, 6, "once");
}

/// Outside a record pass the keys step-enter, as a click does; keys held together are a chord at
/// one position, and the insertion point moves on when the last one comes up (p.1435).
#[test]
fn computer_keys_step_enter_chords_outside_a_record_pass() {
    let mut h = harness();
    let track = h.state_mut().run("track.new", json!({"kind": "instrument"})).unwrap()["tracks"][0].clone();
    let clip = h.state_mut().run("midi.new_clip", json!({"track": track, "start": 0, "end": 96_000})).unwrap()["clip"].clone();
    // The insertion point at the clip's start on its track, the target for step input.
    h.state_mut().run("edit.select", json!({"tracks": [track], "start": 0, "end": 0})).unwrap();
    h.run_steps(2);
    down(&mut h, Key::A);
    down(&mut h, Key::D);
    let at = |h: &AppHarness| h.state().engine.session().edit.selection.start;
    assert_eq!(at(&h), 0, "held keys do not move on");
    up(&mut h, Key::A);
    up(&mut h, Key::D);
    assert!(at(&h) > 0, "the last key up moves on");
    let notes = h.state_mut().run("midi.notes", json!({"clip": clip})).unwrap();
    let notes = notes["notes"].as_array().cloned().unwrap_or_default();
    assert_eq!(notes.len(), 2, "{notes:?}");
    assert_eq!(notes[0]["start"], notes[1]["start"], "a chord: {notes:?}");
}

/// The Computer Keyboard switch reads as a button whether it is on or off, says its state to
/// assistive technology, explains itself in a tooltip, and the window says when the letters go to
/// the shortcuts instead.
#[test]
fn the_computer_keyboard_switch_shows_its_state() {
    use egui::accesskit::{Role, Toggled};
    const OFF_HINT: &str = "Computer Keyboard off: keys go to shortcuts";
    let mut h = harness();
    let state = |h: &AppHarness| h.get_by_role_and_label(Role::Button, "Computer Keyboard").accesskit_node().toggled();
    assert_eq!(state(&h), Some(Toggled::True), "on when the window opens");
    assert!(h.query_by_label(OFF_HINT).is_none(), "no hint while on");
    h.get_by_role_and_label(Role::Button, "Computer Keyboard").hover();
    h.run_steps(30);
    assert!(h.query_by_label_contains("A to K play the octave").is_some(), "the tooltip says what the keys do");
    h.get_by_role_and_label(Role::Button, "Computer Keyboard").click();
    h.run_steps(2);
    assert_eq!(state(&h), Some(Toggled::False), "off after a click");
    assert!(h.query_by_label(OFF_HINT).is_some(), "the window says where the keys go now");
    h.get_by_role_and_label(Role::Button, "Computer Keyboard").click();
    h.run_steps(2);
    assert_eq!(state(&h), Some(Toggled::True));
    assert!(h.query_by_label(OFF_HINT).is_none());
}

/// No key the window uses, typed with or without Shift, with the switch on or off, opens the New
/// Tracks dialog (seen once during a hand test with rapid key presses).
#[test]
fn the_window_s_keys_never_open_new_tracks() {
    let mut h = harness();
    h.state_mut().run("options.keyboard_focus", json!({"focus": "commands"})).unwrap();
    let keys = [
        Key::A,
        Key::W,
        Key::S,
        Key::E,
        Key::D,
        Key::F,
        Key::T,
        Key::G,
        Key::Y,
        Key::H,
        Key::U,
        Key::J,
        Key::K,
        Key::Z,
        Key::X,
        Key::C,
        Key::V,
        Key::N,
    ];
    for on in [true, false] {
        h.state_mut().ui.midi_keyboard_computer_keys = on;
        for k in keys {
            for mods in [Modifiers::NONE, Modifiers::SHIFT] {
                key(&mut h, k, true, mods);
                key(&mut h, k, false, mods);
                assert_eq!(h.state().dialogs.open_name(), None, "{k:?} {mods:?} switch on: {on}");
                // Shift+K closes the window: open it again.
                h.state_mut().ui.show_midi_keyboard = true;
            }
        }
    }
}
