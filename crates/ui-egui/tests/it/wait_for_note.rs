//! Wait for Note (Pro Tools Reference Guide p. 812–813): with it on, Record from stop waits, and
//! the first MIDI event a record-enabled MIDI or instrument track listens to starts the pass, in
//! place of Play (p. 818 step 5, p. 828 step 8), without the pre-roll (p. 812). It cannot be on
//! with Count Off (p. 812). F11 turns it on and off when the MIDI preference says so (p. 175).
use egui::{Event, Key, Modifiers, vec2};
use egui_kittest::{
    Harness,
    kittest::{NodeT, Queryable},
};
use serde_json::json;
use soundcraft_playback::midi::MidiInputs;
use soundcraft_ui_egui::{Services, SoundApp};

const RATE: i64 = 48_000;

/// The app with two connected (simulated) MIDI devices, the Transport window with its MIDI
/// controls open, and an instrument track record-enabled.
fn armed() -> (Harness<'static, SoundApp>, u64) {
    let mut app = SoundApp::new(soundcraft_engine::Engine::default(), None, Services::default());
    app.midi_inputs = Some(MidiInputs::with_port_names(Vec::new(), vec!["Keys".to_string(), "Pad".to_string()]));
    app.ui.show_transport = true;
    let mut h =
        Harness::builder().with_context_setup(soundcraft_ui_egui::framework::install_headless).with_size(vec2(1600.0, 1000.0)).build_ui_state(
            |ui, app: &mut SoundApp| {
                app.logic(&ui.ctx().clone());
                app.ui(ui);
            },
            app,
        );
    let synth = h.state_mut().run("track.new", json!({"name": "Synth", "kind": "instrument"})).unwrap()["tracks"][0].as_u64().unwrap();
    h.state_mut().run("mix.record_arm", json!({"tracks": [synth], "value": true})).unwrap();
    h.state_mut().engine.session_mut().edit.set_flag("view.transport.midi_controls", true);
    h.run_steps(3);
    (h, synth)
}

fn key(h: &mut Harness<'_, SoundApp>, key: Key) {
    h.event(Event::Key { key, physical_key: None, pressed: true, repeat: false, modifiers: Modifiers::NONE });
    h.run_steps(1);
    h.event(Event::Key { key, physical_key: None, pressed: false, repeat: false, modifiers: Modifiers::NONE });
    h.run_steps(2);
}

fn click(h: &mut Harness<'_, SoundApp>, label: &str) {
    h.get_by_label(label).click();
    h.run_steps(3);
}

/// Sends `bytes` from the device `name`.
fn play(h: &mut Harness<'_, SoundApp>, name: &str, bytes: &[u8]) {
    let feed = std::sync::Arc::clone(h.state().midi_inputs.as_ref().unwrap().feed());
    feed.receive(feed.ports().assign(name), bytes);
    h.run_steps(3);
}

/// (record ready, waiting for a note, recording) as `transport.status` reports them.
fn state(h: &mut Harness<'_, SoundApp>) -> (bool, bool, bool) {
    let s = h.state_mut().run("transport.status", json!({})).unwrap();
    (s["record_ready"].as_bool().unwrap(), s["waiting_for_note"].as_bool().unwrap(), s["recording"].as_bool().unwrap())
}

fn wait_for_note(h: &Harness<'_, SoundApp>) -> bool {
    h.state().wait_for_note()
}

#[test]
fn the_wait_for_note_buttons_switch_it_and_count_off_off() {
    let (mut h, _) = armed();
    // One in the Transport window's MIDI controls, one in the toolbar's.
    assert_eq!(h.query_all_by_label("Wait for Note").count(), 2);
    h.state_mut().run("options.countoff", json!({"value": true})).unwrap();
    h.run_steps(2);
    h.query_all_by_label("Wait for Note").next().unwrap().click();
    h.run_steps(3);
    assert!(wait_for_note(&h));
    assert!(!h.state().engine.session().edit.countoff, "Count Off is switched off (p. 812)");
    for node in h.query_all_by_label("Wait for Note") {
        assert_eq!(node.accesskit_node().toggled(), Some(egui::accesskit::Toggled::True), "it says that it is on");
    }
    // Count Off on switches it off again; the toolbar key switches it too.
    h.state_mut().run("options.countoff", json!({})).unwrap();
    h.run_steps(2);
    assert!(!wait_for_note(&h));
    h.query_all_by_label("Wait for Note").last().unwrap().click();
    h.run_steps(3);
    assert!(wait_for_note(&h) && !h.state().engine.session().edit.countoff);
}

#[test]
fn record_waits_and_the_first_note_starts_the_pass_at_the_start_without_pre_roll() {
    let (mut h, _) = armed();
    h.state_mut().run("options.wait_for_note", json!({"value": true})).unwrap();
    // A pre-roll of a second: Wait for Note ignores it (p. 812).
    h.state_mut().run("options.pre_roll", json!({"length": RATE})).unwrap();
    h.state_mut().run("options.pre_post_roll", json!({"value": true})).unwrap();
    h.state_mut().run("transport.locate", json!({"at": 2 * RATE})).unwrap();
    h.run_steps(2);
    click(&mut h, "transport.record_ready");
    assert_eq!(state(&mut h), (true, true, false), "waiting, nothing rolls: {}", h.state().ui.status);
    assert!(h.state().ui.status.starts_with("Wait for Note"), "{}", h.state().ui.status);
    h.run_steps(10);
    assert_eq!(h.state().position(), 2 * RATE, "the counter stands at the start point");
    // The release of a key held from before is not the start of anything.
    play(&mut h, "Keys", &[0x80, 60, 0]);
    play(&mut h, "Keys", &[0x90, 60, 0]);
    assert_eq!(state(&mut h), (true, true, false));
    play(&mut h, "Keys", &[0x90, 60, 100]);
    assert_eq!(state(&mut h), (false, false, true), "the note starts the pass: {}", h.state().ui.status);
    let at = h.state().position();
    assert!((2 * RATE..2 * RATE + RATE / 2).contains(&at), "from the start point, not a second before it: {at}");
    assert!(!h.state().ui.status.starts_with("Wait for Note"), "{}", h.state().ui.status);
}

#[test]
fn only_what_the_track_would_record_starts_the_pass() {
    let (mut h, synth) = armed();
    h.state_mut().run("options.wait_for_note", json!({"value": true})).unwrap();
    // The track listens to Keys on channel 2, and the MIDI Input Filter keeps controllers out.
    h.state_mut().run("track.input", json!({"tracks": [synth], "input": "MIDI:2:Keys"})).unwrap();
    h.state_mut().run("setup.midi_input_filter", json!({"filter": ["cc"]})).unwrap();
    h.run_steps(2);
    click(&mut h, "transport.record_ready");
    play(&mut h, "Pad", &[0x91, 60, 100]);
    play(&mut h, "Keys", &[0x90, 60, 100]);
    play(&mut h, "Keys", &[0xB1, 1, 64]);
    assert_eq!(state(&mut h), (true, true, false), "another device, another channel, a filtered kind");
    // Other data than notes counts (p. 812: "the first note, or other MIDI data").
    play(&mut h, "Keys", &[0xE1, 0, 70]);
    assert_eq!(state(&mut h), (false, false, true), "{}", h.state().ui.status);
}

#[test]
fn stop_or_record_again_while_waiting_records_nothing_and_a_later_note_starts_nothing() {
    let (mut h, _) = armed();
    h.state_mut().run("options.wait_for_note", json!({"value": true})).unwrap();
    let undo = h.state().engine.undo_label().map(str::to_owned);
    for cancel in ["transport.record_ready", "transport.stop"] {
        click(&mut h, "transport.record_ready");
        assert_eq!(state(&mut h), (true, true, false));
        click(&mut h, cancel);
        assert_eq!(state(&mut h), (false, false, false), "{cancel} cancels the wait");
        assert!(h.state().ui.status.is_empty(), "{cancel}: {}", h.state().ui.status);
        play(&mut h, "Keys", &[0x90, 60, 100]);
        assert_eq!(state(&mut h), (false, false, false), "{cancel}: the note after it starts nothing");
    }
    assert!(h.state().engine.session().tracks[0].clips().is_empty());
    assert_eq!(h.state().engine.undo_label().map(str::to_owned), undo, "no undo step");
}

#[test]
fn f12_waits_too_and_play_still_starts_the_pass_at_once() {
    let (mut h, _) = armed();
    h.state_mut().run("options.wait_for_note", json!({"value": true})).unwrap();
    h.run_steps(2);
    key(&mut h, Key::F12);
    assert_eq!(state(&mut h), (true, true, false), "F12 waits for the note as Record does");
    key(&mut h, Key::F12);
    assert_eq!(state(&mut h), (false, false, false), "and again cancels");
    click(&mut h, "transport.record_ready");
    click(&mut h, "transport.play");
    assert_eq!(state(&mut h), (false, false, true), "Play does not wait");
}

#[test]
fn with_only_audio_tracks_record_does_not_wait_and_says_why() {
    let (mut h, synth) = armed();
    h.state_mut().run("options.wait_for_note", json!({"value": true})).unwrap();
    h.state_mut().run("mix.record_arm", json!({"tracks": [synth], "value": false})).unwrap();
    let vox = h.state_mut().run("track.new", json!({"name": "Vox", "format": "mono"})).unwrap()["tracks"][0].as_u64().unwrap();
    h.state_mut().run("mix.record_arm", json!({"tracks": [vox], "value": true})).unwrap();
    h.run_steps(2);
    click(&mut h, "transport.record_ready");
    assert_eq!(state(&mut h), (true, false, false), "Record Ready, not waiting");
    assert!(h.state().ui.status.contains("Wait for Note waits only for MIDI"), "{}", h.state().ui.status);
}

#[test]
fn no_device_to_wait_for_says_so_and_a_device_unplugged_while_waiting_cancels_the_wait() {
    let (mut h, synth) = armed();
    h.state_mut().run("options.wait_for_note", json!({"value": true})).unwrap();
    // The track listens to a device that is not connected.
    h.state_mut().run("track.input", json!({"tracks": [synth], "input": "MIDI:*:Gone"})).unwrap();
    h.run_steps(2);
    click(&mut h, "transport.record_ready");
    assert_eq!(state(&mut h), (false, false, false));
    assert!(h.state().ui.status.starts_with("Cannot wait for a note"), "{}", h.state().ui.status);
    // Waiting for Keys, which goes away.
    h.state_mut().run("track.input", json!({"tracks": [synth], "input": "MIDI:*:Keys"})).unwrap();
    h.run_steps(2);
    click(&mut h, "transport.record_ready");
    assert_eq!(state(&mut h), (true, true, false));
    h.state_mut().midi_inputs.as_mut().unwrap().set_port_names(vec!["Pad".to_string()]);
    h.state_mut().midi_inputs.as_mut().unwrap().rescan();
    h.run_steps(3);
    assert_eq!(state(&mut h), (false, false, false), "not left waiting for a device that is gone");
    assert!(h.state().ui.status.starts_with("Wait for Note cancelled"), "{}", h.state().ui.status);
}

#[test]
fn f11_switches_wait_for_note_only_when_the_preference_is_on() {
    let (mut h, _) = armed();
    key(&mut h, Key::F11);
    assert!(!wait_for_note(&h), "off by default (on a Mac F11 is Show Desktop)");
    // The preference is a working checkbox now, not a placeholder.
    h.state_mut().ui.show_preferences = true;
    h.state_mut().ui.preferences_page = soundcraft_ui_egui::preferences::PreferencesPage::Midi;
    h.run_steps(3);
    let check = h.get_by_label("Use F11 for Wait for Note");
    assert!(!check.accesskit_node().is_disabled());
    check.click();
    h.run_steps(2);
    h.get_by_label("OK").click();
    h.run_steps(3);
    assert!(h.state().ui.f11_wait_for_note);
    key(&mut h, Key::F11);
    assert!(wait_for_note(&h));
    key(&mut h, Key::F11);
    assert!(!wait_for_note(&h));
}
