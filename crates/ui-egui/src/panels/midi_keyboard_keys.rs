//! The MIDI Keyboard window's computer keys (#1209). Pro Tools Reference Guide p.827: "if you press A
//! on your computer keyboard, it plays C; if you press T on the keyboard, it plays F#/Gb", one octave
//! at a time, moved "from –C2 to C8 using the Z and X keys", with the velocity changed "from 1–127
//! using the C and V keys".
//!
//! While the window is open with its Computer Keyboard switch on, these keys (unmodified) play
//! instead of running a shortcut, whenever the shortcuts would get them; [`takes`] tells `shortcuts::handle` which ones. A note starts when
//! its key goes down and ends when it comes up, or when the switch goes off, the window closes, a
//! text field or dialog takes the keyboard, or the app loses focus.

use crate::SoundApp;
use egui::{Key, Modifiers};

/// The keys that play the octave, from its C up to the next C, and the letter shown on each.
pub(crate) const NOTE_KEYS: [(Key, &str); 13] = [
    (Key::A, "A"),
    (Key::W, "W"),
    (Key::S, "S"),
    (Key::E, "E"),
    (Key::D, "D"),
    (Key::F, "F"),
    (Key::T, "T"),
    (Key::G, "G"),
    (Key::Y, "Y"),
    (Key::H, "H"),
    (Key::U, "U"),
    (Key::J, "J"),
    (Key::K, "K"),
];
const OCTAVE_DOWN: Key = Key::Z;
const OCTAVE_UP: Key = Key::X;
const VELOCITY_DOWN: Key = Key::C;
const VELOCITY_UP: Key = Key::V;
/// The octave's lowest note goes from C-2 (0) to C8 (120).
const HIGHEST_OCTAVE: u8 = 120;
/// How much one press of C or V changes the velocity.
const VELOCITY_STEP: u8 = 10;

/// The keys held down and the notes they started, and whether a step-entered note waits for the
/// last key to come up before the insertion point moves on.
#[derive(Clone, Default)]
struct Held {
    keys: Vec<(Key, u8)>,
    stepped: bool,
}

fn held_id() -> egui::Id {
    egui::Id::unique("midi-keyboard-computer-keys")
}

/// The key a key event is about: where it sits (so the letters match the window on any layout)
/// when the platform says, else what it types.
fn position(key: Key, physical: Option<Key>) -> Key {
    physical.unwrap_or(key)
}

fn is_mapped(key: Key) -> bool {
    NOTE_KEYS.iter().any(|(k, _)| *k == key) || matches!(key, OCTAVE_DOWN | OCTAVE_UP | VELOCITY_DOWN | VELOCITY_UP)
}

/// Whether the window's computer keys are on: it is open and its switch is on.
pub(crate) fn active(app: &SoundApp) -> bool {
    app.ui.show_midi_keyboard && app.ui.midi_keyboard_computer_keys
}

/// Whether the MIDI Keyboard window takes this key press instead of a shortcut. Keys with a
/// modifier (Shift+K, Cmd+Z) and keys it does not use (Space, Return) still run their shortcuts.
pub(crate) fn takes(app: &SoundApp, key: Key, physical: Option<Key>, mods: Modifiers) -> bool {
    active(app) && mods.is_none() && is_mapped(position(key, physical))
}

/// The lowest note of the octave the computer keys play.
pub(crate) fn octave(app: &SoundApp) -> u8 {
    (app.ui.midi_keyboard_octave.min(HIGHEST_OCTAVE) / 12) * 12
}

/// The velocity the window plays at.
pub(crate) fn velocity(app: &SoundApp) -> u8 {
    app.ui.midi_keyboard_velocity.clamp(1, 127)
}

/// The notes the computer keys hold down now.
pub(crate) fn held_notes(ctx: &egui::Context) -> Vec<u8> {
    ctx.data(|d| d.get_temp::<Held>(held_id())).map(|h| h.keys.iter().map(|(_, n)| *n).collect()).unwrap_or_default()
}

/// Let go of every note the computer keys hold.
pub(crate) fn release(app: &mut SoundApp, ctx: &egui::Context) {
    let Some(held) = ctx.data_mut(|d| d.remove_temp::<Held>(held_id())) else { return };
    for (_, n) in held.keys {
        super::windows::keyboard_send(app, [0x80, n, 0]);
    }
    if held.stepped {
        super::windows::step_advance(app);
    }
}

/// Play this pass's key presses and releases. Runs every pass, open or not, so a held note always
/// ends.
pub(crate) fn update(app: &mut SoundApp, ctx: &egui::Context) {
    let listening = active(app) && !crate::framework::widget_has_keyboard(ctx) && !crate::shortcuts::dialog_open(app);
    // Losing focus ends the held notes: their keys may come up in another app. Keys still play
    // while unfocused, as shortcuts do, so a script's `ui.key` plays too.
    if !listening || !ctx.input(|i| i.focused) {
        release(app, ctx);
    }
    if !listening {
        return;
    }
    let events: Vec<(Key, bool, bool, Modifiers)> = ctx.input(|i| {
        i.events
            .iter()
            .filter_map(|e| match e {
                egui::Event::Key { key, physical_key, pressed, repeat, modifiers } => {
                    Some((position(*key, *physical_key), *pressed, *repeat, *modifiers))
                }
                _ => None,
            })
            .collect()
    });
    if events.is_empty() {
        return;
    }
    let mut held: Held = ctx.data(|d| d.get_temp(held_id())).unwrap_or_default();
    for (key, pressed, repeat, mods) in events {
        if !pressed {
            // A key comes up with whatever modifiers are held then: let it go either way.
            if let Some(i) = held.keys.iter().position(|(k, _)| *k == key) {
                let (_, n) = held.keys.remove(i);
                super::windows::keyboard_send(app, [0x80, n, 0]);
                if held.keys.is_empty() && std::mem::take(&mut held.stepped) {
                    super::windows::step_advance(app);
                }
            }
            continue;
        }
        if repeat || !mods.is_none() {
            continue;
        }
        match key {
            OCTAVE_DOWN => app.ui.midi_keyboard_octave = octave(app).saturating_sub(12),
            OCTAVE_UP => app.ui.midi_keyboard_octave = (octave(app) + 12).min(HIGHEST_OCTAVE),
            VELOCITY_DOWN => app.ui.midi_keyboard_velocity = velocity(app).saturating_sub(VELOCITY_STEP).max(1),
            VELOCITY_UP => app.ui.midi_keyboard_velocity = velocity(app).saturating_add(VELOCITY_STEP).min(127),
            _ => {
                let Some(i) = NOTE_KEYS.iter().position(|(k, _)| *k == key) else { continue };
                // The octave at C8 reaches past G8, the highest MIDI note: those keys stay silent.
                let Some(n) = u8::try_from(usize::from(octave(app)) + i).ok().filter(|n| *n <= 127) else { continue };
                if held.keys.iter().any(|(k, _)| *k == key) {
                    continue;
                }
                super::windows::keyboard_send(app, [0x90, n, velocity(app)]);
                held.keys.push((key, n));
                // Keys held together step-enter as a chord at one position (p.1435: the insertion
                // point moves on when the note is released).
                held.stepped |= super::windows::step_add(app, n);
            }
        }
    }
    ctx.data_mut(|d| d.insert_temp(held_id(), held));
}
