//! Setup › MIDI › MIDI Studio opens the system's MIDI studio setup, where MIDI devices are named,
//! as Pro Tools does on macOS (Reference Guide p.196: "In Pro Tools, choose Setup > MIDI > MIDI
//! Studio" launches Audio MIDI Setup). Where the system has none, the item says so.
use egui::vec2;
use egui_kittest::Harness;
use serde_json::json;
use soundcraft_playback::midi::MidiInputs;
use soundcraft_ui_egui::{Services, SoundApp, menus};
use std::cell::Cell;
use std::rc::Rc;

const PATH: &str = "Setup > MIDI > MIDI Studio...";

/// The app with two stand-in MIDI devices, and the system's MIDI setup when `opens` is set: it
/// counts how often it is opened.
fn harness(opens: Option<Rc<Cell<u32>>>) -> Harness<'static, SoundApp> {
    let services = Services {
        open_midi_studio: opens.map(|count| {
            Box::new(move || {
                count.set(count.get() + 1);
                Ok("Audio MIDI Setup".to_string())
            }) as soundcraft_ui_egui::OpenMidiStudioFn
        }),
        ..Default::default()
    };
    let mut app = SoundApp::new(soundcraft_engine::Engine::default(), None, services);
    app.midi_inputs = Some(MidiInputs::with_port_names(Vec::new(), vec!["Keys".into(), "Drum Pad".into()]));
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

#[test]
fn the_menu_item_opens_the_system_midi_setup() {
    let opened = Rc::new(Cell::new(0));
    let mut h = harness(Some(opened.clone()));
    menus::invoke_menu(h.state_mut(), "setup.midi_studio", PATH);
    h.run_steps(2);
    assert_eq!(opened.get(), 1, "the menu opened it once");
    assert!(h.state().ui.status.contains("Audio MIDI Setup"), "the status line says what opened: {}", h.state().ui.status);
}

#[test]
fn without_a_system_midi_setup_the_item_says_so() {
    let mut h = harness(None);
    let before = h.state().ui.status.clone();
    menus::invoke_menu(h.state_mut(), "setup.midi_studio", PATH);
    h.run_steps(2);
    let status = h.state().ui.status.clone();
    assert_ne!(status, before, "the item does not do nothing");
    assert!(status.contains("not available"), "{status}");
    let reply = h.state_mut().run("setup.midi_studio", json!({"open": true}));
    assert!(reply.is_err(), "a script asking to open it is told it did not: {reply:?}");
}

#[test]
fn a_script_opens_it_only_when_asked_and_reads_the_devices_as_the_system_names_them() {
    let opened = Rc::new(Cell::new(0));
    let mut h = harness(Some(opened.clone()));
    let reply = h.state_mut().run("setup.midi_studio", json!({})).unwrap();
    assert_eq!(opened.get(), 0, "a programmatic call opens nothing by itself");
    assert_eq!(reply["ports"], json!(["Keys", "Drum Pad"]), "{reply}");
    assert_eq!(reply["opened"], json!(null), "{reply}");
    let reply = h.state_mut().run("setup.midi_studio", json!({"open": true})).unwrap();
    assert_eq!(opened.get(), 1);
    assert_eq!(reply["opened"], json!("Audio MIDI Setup"), "{reply}");
}
