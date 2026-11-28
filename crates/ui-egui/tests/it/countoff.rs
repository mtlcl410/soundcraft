//! Count Off: with Options › Count Off on, a start from stop clicks the bars Setup ›
//! Click/Countoff sets before the transport rolls, and recording starts at the end of them (Pro
//! Tools Reference Guide p. 271, p. 767, p. 788 step 9, p. 818 step 5).
use egui::{Event, Key, Modifiers, vec2};
use egui_kittest::{Harness, kittest::Queryable};
use serde_json::json;
use soundcraft_playback::midi::MidiInputs;
use soundcraft_ui_egui::{Services, SoundApp};
use std::time::Duration;

const RATE: i64 = 48_000;

/// The app with a connected (simulated) MIDI device, the Transport window and its MIDI controls
/// open, an instrument track record-enabled, the click and Count Off on (2 bars, 4/4 at 120 bpm:
/// 4 s) and the clock frozen: time only moves with [`wait`].
fn counting() -> Harness<'static, SoundApp> {
    let mut app = SoundApp::new(soundcraft_engine::Engine::default(), None, Services::default());
    app.midi_inputs = Some(MidiInputs::with_port_names(Vec::new(), vec!["Keys".to_string()]));
    app.ui.show_transport = true;
    app.advance_test_clock(Duration::ZERO);
    let mut h =
        Harness::builder().with_context_setup(soundcraft_ui_egui::framework::install_headless).with_size(vec2(1600.0, 1000.0)).build_ui_state(
            |ui, app: &mut SoundApp| {
                app.logic(&ui.ctx().clone());
                app.ui(ui);
            },
            app,
        );
    let app = h.state_mut();
    let synth = app.run("track.new", json!({"name": "Synth", "kind": "instrument"})).unwrap()["tracks"][0].as_u64().unwrap();
    app.run("mix.record_arm", json!({"tracks": [synth], "value": true})).unwrap();
    app.run("view.transport_midi_controls", json!({"value": true})).unwrap();
    app.run("options.click", json!({"value": true})).unwrap();
    app.run("options.countoff", json!({"value": true})).unwrap();
    h.run_steps(3);
    h
}

/// Let `seconds` pass, in frames of at most a quarter of a second.
fn wait(h: &mut Harness<'_, SoundApp>, seconds: f64) {
    let mut left = seconds;
    while left > 1e-9 {
        let step = left.min(0.25);
        h.state_mut().advance_test_clock(Duration::from_secs_f64(step));
        h.step();
        left -= step;
    }
}

fn key(h: &mut Harness<'_, SoundApp>, key: Key, modifiers: Modifiers) {
    h.event(Event::Key { key, physical_key: None, pressed: true, repeat: false, modifiers });
    h.step();
    h.event(Event::Key { key, physical_key: None, pressed: false, repeat: false, modifiers });
    h.step();
}

fn click(h: &mut Harness<'_, SoundApp>, label: &str) {
    h.get_by_label(label).click();
    h.step();
    h.step();
}

/// `transport.status` as the scripts see it.
fn status(h: &mut Harness<'_, SoundApp>) -> serde_json::Value {
    h.state_mut().run("transport.status", json!({})).unwrap()
}

fn counting_off(h: &mut Harness<'_, SoundApp>) -> bool {
    status(h)["counting_off"].as_bool().unwrap()
}

#[test]
fn record_ready_and_play_count_off_two_bars_then_record_from_the_insertion() {
    let mut h = counting();
    h.state_mut().run("transport.locate", json!({"at": RATE})).unwrap();
    h.step();
    click(&mut h, "transport.record_ready");
    click(&mut h, "transport.play");
    let s = status(&mut h);
    assert_eq!((s["playing"].as_bool(), s["recording"].as_bool(), s["counting_off"].as_bool()), (Some(true), Some(true), Some(true)), "{s}");
    assert_eq!(s["countoff_left"].as_i64(), Some(4 * RATE), "2 bars of 4/4 at 120 bpm");
    assert_eq!(h.state().position(), RATE, "the counter stands at the start point");
    assert!(h.state().ui.status.contains("Counting off: bar 1 of 2"), "{}", h.state().ui.status);
    h.get_by_label("Count Off 1/2");
    wait(&mut h, 2.5);
    assert_eq!(h.state().position(), RATE, "still counting");
    assert!(h.state().ui.status.contains("bar 2 of 2"), "{}", h.state().ui.status);
    h.get_by_label("Count Off 2/2");
    wait(&mut h, 1.5);
    assert!(!counting_off(&mut h), "4 s later the count-off is over");
    wait(&mut h, 0.5);
    let at = h.state().position();
    assert_eq!(at, RATE + RATE / 2, "the pass rolls from the start point as the count-off ends");
    assert!(h.state().engine.transport.recording);
    assert!(h.state().ui.status.is_empty(), "the count's message goes: {}", h.state().ui.status);
    h.get_by_label("Count Off");
}

#[test]
fn f12_and_play_count_off_too_unless_the_count_off_is_only_for_recording() {
    let mut h = counting();
    key(&mut h, Key::F12, Modifiers::NONE);
    assert!(counting_off(&mut h), "F12 from stop counts off");
    assert!(h.state().engine.transport.recording);
    click(&mut h, "transport.stop");
    click(&mut h, "transport.play");
    assert!(counting_off(&mut h), "Play counts off (p. 767: \"when recording or playing\")");
    assert!(!h.state().engine.transport.recording);
    click(&mut h, "transport.stop");
    h.state_mut().run("setup.click_countoff", json!({"countoff_only_record": true})).unwrap();
    click(&mut h, "transport.play");
    assert!(!counting_off(&mut h) && h.state().is_playing(), "only when recording: Play starts at once");
    // Punching in while playing never counts off.
    click(&mut h, "transport.record_ready");
    assert!(!counting_off(&mut h) && h.state().engine.transport.recording, "punched in at once");
    click(&mut h, "transport.stop");
    click(&mut h, "transport.record_ready");
    click(&mut h, "transport.play");
    assert!(counting_off(&mut h), "a record pass still counts off");
}

#[test]
fn stop_during_the_count_off_records_nothing_and_leaves_no_undo_step() {
    let mut h = counting();
    h.state_mut().run("transport.locate", json!({"at": 2 * RATE})).unwrap();
    h.step();
    let undo = h.state().engine.undo_label().map(str::to_owned);
    key(&mut h, Key::F12, Modifiers::NONE);
    wait(&mut h, 1.0);
    click(&mut h, "transport.stop");
    let s = status(&mut h);
    assert_eq!((s["playing"].as_bool(), s["recording"].as_bool(), s["counting_off"].as_bool()), (Some(false), Some(false), Some(false)));
    assert_eq!(h.state().position(), 2 * RATE, "the transport never left the start point");
    assert_eq!(h.state().engine.session().tracks[0].clips().len(), 0, "nothing recorded");
    assert_eq!(h.state().engine.undo_label().map(str::to_owned), undo, "no undo step");
    assert_eq!(h.state().ui.status, "Stopped during the count-off: nothing was recorded.");
}

/// Count-off, then the pre-roll, then recording at the punch-in point (Pro Tools forums: "count-in
/// click first, then click during pre-roll, punch-in, and post-roll"; the guide is silent).
#[test]
fn the_count_off_comes_before_the_pre_roll_and_the_punch() {
    let mut h = counting();
    let app = h.state_mut();
    app.run("edit.select", json!({"start": 3 * RATE, "end": 4 * RATE})).unwrap();
    app.run("options.pre_post_roll", json!({"value": true})).unwrap();
    app.run("options.pre_roll", json!({"length": RATE})).unwrap();
    h.step();
    click(&mut h, "transport.record_ready");
    click(&mut h, "transport.play");
    assert!(counting_off(&mut h));
    assert_eq!(h.state().position(), 2 * RATE, "the count-off leads into the pre-roll");
    wait(&mut h, 4.5);
    assert!(!counting_off(&mut h));
    assert_eq!(h.state().position(), 2 * RATE + RATE / 2, "the pre-roll plays after the count-off");
}

/// The count-off is in the meter and at the tempo where the transport starts: 3/4 at 90 bpm, 2
/// bars = 6 beats of 2/3 s = 4 s; 1 bar of 7/8 at 120 bpm = 7 eighths = 1.75 s; and the bars come
/// from Setup › Click/Countoff.
#[test]
fn the_count_off_follows_the_meter_and_tempo_at_the_start_and_the_bar_count() {
    let mut h = counting();
    {
        let s = h.state_mut().engine.session_mut();
        let bar3 = s.tempo.bar_start_tick(3);
        s.tempo.set_tempo(bar3, 90.0).unwrap();
        s.tempo.set_meter(bar3, 3, 4).unwrap();
    }
    let bar3 = {
        let s = h.state().engine.session();
        s.tempo.tick_to_samples(s.tempo.bar_start_tick(3), s.sample_rate)
    };
    h.state_mut().run("transport.locate", json!({"at": bar3})).unwrap();
    h.step();
    click(&mut h, "transport.play");
    assert_eq!(status(&mut h)["countoff_left"].as_i64(), Some(4 * RATE), "3/4 at 90 bpm");
    click(&mut h, "transport.stop");
    {
        let s = h.state_mut().engine.session_mut();
        s.tempo.set_meter(0, 7, 8).unwrap();
    }
    h.state_mut().run("setup.click_countoff", json!({"countoff_bars": 1})).unwrap();
    h.state_mut().run("transport.locate", json!({"at": 0})).unwrap();
    h.step();
    click(&mut h, "transport.play");
    assert_eq!(status(&mut h)["countoff_left"].as_i64(), Some(RATE * 7 / 4), "1 bar of 7/8 at 120 bpm");
    h.get_by_label("Count Off 1/1");
}

/// Loop Record counts off once, before the first pass; the loop goes round without another.
#[test]
fn loop_record_counts_off_only_before_the_first_pass() {
    let mut h = counting();
    let app = h.state_mut();
    app.run("edit.select", json!({"start": RATE, "end": 2 * RATE})).unwrap();
    app.run("options.loop_record", json!({"value": true})).unwrap();
    h.step();
    click(&mut h, "transport.record_ready");
    click(&mut h, "transport.play");
    assert!(counting_off(&mut h));
    wait(&mut h, 4.0);
    for _ in 0..12 {
        wait(&mut h, 0.25);
        assert!(!counting_off(&mut h), "no count-off as the loop goes round");
        let at = h.state().position();
        assert!((RATE..2 * RATE).contains(&at), "{at}");
    }
}

/// With the click off the count-off still waits its bars, as Pro Tools does, and says the click
/// is off rather than leaving a silent wait unexplained.
#[test]
fn with_the_click_off_the_count_off_waits_and_says_the_click_is_off() {
    let mut h = counting();
    h.state_mut().run("options.click", json!({"value": false})).unwrap();
    h.step();
    key(&mut h, Key::F12, Modifiers::NONE);
    assert!(counting_off(&mut h));
    assert!(h.state().ui.status.contains("the click is off"), "{}", h.state().ui.status);
}
