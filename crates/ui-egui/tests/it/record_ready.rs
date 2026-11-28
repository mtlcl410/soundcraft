//! Record Ready: from stop, the Record button arms the transport (it flashes) and nothing rolls;
//! Play or Space then starts the pass, and Record again or Stop disarms (Pro Tools Reference Guide
//! p. 788 steps 7 and 9, p. 269). F12 and Cmd+Space (Ctrl+Space) still record at once (p. 789).
use egui::{Event, Key, Modifiers, vec2};
use egui_kittest::{
    Harness,
    kittest::{NodeT, Queryable},
};
use serde_json::json;
use soundcraft_playback::midi::MidiInputs;
use soundcraft_ui_egui::{Services, SoundApp};

const RATE: i64 = 48_000;

/// The app with a connected (simulated) MIDI device, the Transport window open, and an instrument
/// track record-enabled: a pass on it needs no audio device.
fn armed() -> Harness<'static, SoundApp> {
    let mut app = SoundApp::new(soundcraft_engine::Engine::default(), None, Services::default());
    app.midi_inputs = Some(MidiInputs::with_port_names(Vec::new(), vec!["Keys".to_string()]));
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
    h.run_steps(3);
    h
}

fn key(h: &mut Harness<'_, SoundApp>, key: Key, modifiers: Modifiers) {
    h.event(Event::Key { key, physical_key: None, pressed: true, repeat: false, modifiers });
    h.run_steps(1);
    h.event(Event::Key { key, physical_key: None, pressed: false, repeat: false, modifiers });
    h.run_steps(2);
}

fn click(h: &mut Harness<'_, SoundApp>, label: &str) {
    h.get_by_label(label).click();
    h.run_steps(3);
}

/// (record ready, playing, recording) as the app and `transport.status` report them.
fn state(h: &mut Harness<'_, SoundApp>) -> (bool, bool, bool) {
    let status = h.state_mut().run("transport.status", json!({})).unwrap();
    let ready = status["record_ready"].as_bool().unwrap_or(false);
    (ready, h.state().is_playing(), h.state().engine.transport.recording)
}

#[test]
fn record_from_stop_arms_without_rolling_and_play_starts_the_pass() {
    let mut h = armed();
    h.state_mut().run("transport.locate", json!({"at": RATE})).unwrap();
    h.run_steps(2);
    click(&mut h, "transport.record_ready");
    assert_eq!(state(&mut h), (true, false, false), "armed, nothing rolls");
    let before = h.state().position();
    h.run_steps(10);
    assert_eq!(h.state().position(), before, "the counter does not run in Record Ready");
    assert!(h.state().ui.status.contains("Record Ready"), "{}", h.state().ui.status);
    click(&mut h, "transport.play");
    assert_eq!(state(&mut h), (false, true, true), "Play starts the record pass: {}", h.state().ui.status);
    let at = h.state().position();
    assert!((RATE..RATE + RATE / 2).contains(&at), "the pass starts at the insertion point: {at}");
}

#[test]
fn space_starts_the_pass_and_record_again_or_stop_disarms_without_recording() {
    let mut h = armed();
    click(&mut h, "transport.record_ready");
    key(&mut h, Key::Space, Modifiers::NONE);
    assert_eq!(state(&mut h), (false, true, true), "Space starts it like Play");
    key(&mut h, Key::Space, Modifiers::NONE);
    assert_eq!(state(&mut h), (false, false, false));
    let clips = h.state().engine.session().tracks[0].clips().len();
    let undo = h.state().engine.undo_label().map(str::to_owned);
    for leave in ["transport.record_ready", "transport.stop"] {
        click(&mut h, "transport.record_ready");
        assert!(state(&mut h).0);
        click(&mut h, leave);
        assert_eq!(state(&mut h), (false, false, false), "{leave} leaves Record Ready");
        assert!(h.state().ui.status.starts_with("Record Ready off: "), "{leave} says why: {}", h.state().ui.status);
    }
    assert_eq!(h.state().engine.session().tracks[0].clips().len(), clips, "nothing recorded");
    assert_eq!(h.state().engine.undo_label().map(str::to_owned), undo, "no undo step");
}

#[test]
fn f12_and_command_space_still_record_at_once_also_from_record_ready() {
    for (k, m) in [(Key::F12, Modifiers::NONE), (Key::Space, Modifiers::COMMAND)] {
        let mut h = armed();
        key(&mut h, k, m);
        assert_eq!(state(&mut h), (false, true, true), "{k:?} {m:?} from stop: {}", h.state().ui.status);
        click(&mut h, "transport.stop");
        click(&mut h, "transport.record_ready");
        key(&mut h, k, m);
        assert_eq!(state(&mut h), (false, true, true), "{k:?} {m:?} from Record Ready");
    }
}

#[test]
fn record_while_playing_still_punches_in() {
    let mut h = armed();
    click(&mut h, "transport.play");
    click(&mut h, "transport.record_ready");
    assert_eq!(state(&mut h), (false, true, true), "punched in on the fly");
}

#[test]
fn play_from_record_ready_honours_the_punch_range_and_pre_roll() {
    let mut h = armed();
    let app = h.state_mut();
    app.run("edit.select", json!({"start": 2 * RATE, "end": 3 * RATE})).unwrap();
    app.run("options.pre_post_roll", json!({"value": true})).unwrap();
    app.run("options.pre_roll", json!({"length": RATE / 2})).unwrap();
    h.run_steps(2);
    click(&mut h, "transport.record_ready");
    click(&mut h, "transport.play");
    assert_eq!(state(&mut h), (false, true, true));
    let at = h.state().position();
    assert!((3 * RATE / 2..2 * RATE).contains(&at), "the pass starts with the pre-roll, before the punch: {at}");
}

#[test]
fn record_with_nothing_record_enabled_shows_the_hint_and_does_not_arm() {
    let mut h = armed();
    h.state_mut().run("mix.record_arm", json!({"value": false})).unwrap();
    h.run_steps(2);
    click(&mut h, "transport.record_ready");
    assert_eq!(state(&mut h), (false, false, false));
    assert!(h.state().ui.status.contains("R button"), "#329's hint: {}", h.state().ui.status);
}

#[test]
fn play_in_record_ready_that_cannot_record_says_why_and_leaves_it_stopped() {
    let mut h = armed();
    click(&mut h, "transport.record_ready");
    // The MIDI device goes away while armed: the pass decided at Play time cannot start.
    h.state_mut().midi_inputs.as_mut().unwrap().set_port_names(Vec::new());
    h.state_mut().midi_inputs.as_mut().unwrap().rescan();
    h.run_steps(2);
    click(&mut h, "transport.play");
    assert_eq!(state(&mut h), (false, false, false), "no silent play without recording");
    assert!(h.state().ui.status.contains("Cannot record"), "{}", h.state().ui.status);
}

#[test]
fn a_scripted_play_from_a_position_in_record_ready_records_from_there() {
    let mut h = armed();
    click(&mut h, "transport.record_ready");
    h.state_mut().run("transport.play", json!({"from": 4 * RATE})).unwrap();
    h.run_steps(2);
    assert_eq!(state(&mut h), (false, true, true));
    assert!(h.state().position() >= 4 * RATE, "{}", h.state().position());
}

#[test]
fn the_record_buttons_say_record_ready_to_assistive_technology_while_they_flash() {
    let mut h = armed();
    let tip = if cfg!(target_os = "macos") {
        "Record Ready (record at once: F12 or Cmd+Space)"
    } else {
        "Record Ready (record at once: F12 or Ctrl+Space)"
    };
    let selected = |h: &Harness<'_, SoundApp>| {
        [tip, "transport.record_ready"].map(|label| h.get_by_label(label).accesskit_node().toggled() == Some(egui::accesskit::Toggled::True))
    };
    assert_eq!(selected(&h), [false, false]);
    click(&mut h, "transport.record_ready");
    // The fill goes on and off; the state the buttons report does not.
    for _ in 0..6 {
        h.step();
        assert_eq!(selected(&h), [true, true], "Record Ready, on every frame");
    }
    click(&mut h, "transport.stop");
    assert_eq!(selected(&h), [false, false]);
}
