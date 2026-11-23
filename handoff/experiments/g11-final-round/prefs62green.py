from pathlib import Path
root=Path(__file__).parent/'prefs62'
def rewrite(p,a,b):
    assert a in p.read_text(encoding='utf8'),a
    p.write_text(p.read_text(encoding='utf8').replace(a,b,1),encoding='utf8')
p=root/'crates/ui-egui/src/preferences.rs'
rewrite(p,'    /// Search includes page, section, control, choice and value text.\n    #[test]\n    fn midi_sync_pref_','    #[test]\n    fn midi_sync_pref_')
rewrite(p,'    #[test]\n    fn search_matches_pages_sections','    /// Search includes page, section, control, choice and value text.\n    #[test]\n    fn search_matches_pages_sections')
rewrite(p,'        Control::Check(text) if section == "Delay Compensation for External Devices" => {','''        Control::Check(text @ "MIDI Notes and Controllers") if section == "Delay Compensation for External Devices" => {
            ui.add_enabled(false, egui::Checkbox::new(&mut draft.compensation.notes, label(text)));
            ui.label(crate::localization::text("Takes effect once external MIDI track output is available."));
        }
        Control::Check(text) if section == "Delay Compensation for External Devices" => {''')
rewrite(p,'''            let value = match text {
                "MIDI Beat Clock" => &mut draft.compensation.beat_clock,
                "MIDI Timecode" => &mut draft.compensation.mtc,
                _ => &mut draft.compensation.notes,
            };''','''            let value = if text == "MIDI Beat Clock" { &mut draft.compensation.beat_clock } else { &mut draft.compensation.mtc };''')
p=root/'crates/ui-egui/src/midi_sync.rs'
rewrite(p,'fn valid_port(name: &str) -> bool {','''pub const MAX_SYNC_PORTS: usize = 256;

pub fn valid_saved_offset(samples: i64) -> bool {
    samples.unsigned_abs() <= 10_000_000
}

pub fn valid_port(name: &str) -> bool {''')
rewrite(p,'self.ports.len() > 256 || self.ports.iter().any(|(k, v)| !valid_port(k) || v.offset_samples.unsigned_abs() > 10_000_000)','self.ports.len() > MAX_SYNC_PORTS || self.ports.iter().any(|(k, v)| !valid_port(k) || !valid_saved_offset(v.offset_samples))')
rewrite(p,'self.ui.midi_sync.ports.len() < 256','self.ui.midi_sync.ports.len() < MAX_SYNC_PORTS')
p=root/'apps/soundcraft/src/config.rs'
rewrite(p,'const MAX_UI_BYTES: u64', '''/// Drop only invalid workstation synchronization fields. Serde defaults fill each removed
/// field, leaving unrelated preferences and other members of the same port intact.
fn recover_sync_settings(fields: &mut serde_json::Map<String, serde_json::Value>, resets: &mut Vec<String>) {
    use serde_json::Value;
    use soundcraft_ui_egui::midi_sync::{Compensation, MAX_SYNC_PORTS, MidiSyncPort, valid_port, valid_saved_offset};

    reset_invalid(fields, "midi_sync", "midi_sync", Value::is_object, resets);
    let Some(sync) = fields.get_mut("midi_sync").and_then(Value::as_object_mut) else { return };
    reset_invalid(sync, "enabled", "midi_sync.enabled", Value::is_boolean, resets);
    reset_invalid(sync, "compensation", "midi_sync.compensation", Value::is_object, resets);
    if let Some(compensation) = sync.get_mut("compensation").and_then(Value::as_object_mut) {
        compensation.retain(|key,value| {
            let valid = serde_json::from_value::<Compensation>(serde_json::json!({(key):value})).is_ok();
            if !valid { record_reset(resets, &format!("midi_sync.compensation.{key}")); }
            valid
        });
    }
    reset_invalid(sync, "port_ids", "midi_sync.port_ids", Value::is_object, resets);
    if let Some(ids) = sync.get_mut("port_ids").and_then(Value::as_object_mut) {
        let mut kept = 0;
        ids.retain(|name, value| {
            if !valid_port(name) || kept == MAX_SYNC_PORTS || !value.as_str().is_some_and(valid_port) {
                record_reset(resets, &format!("midi_sync.port_ids.{name}"));
                return false;
            }
            kept += 1;
            true
        });
    }
    reset_invalid(sync, "ports", "midi_sync.ports", Value::is_object, resets);
    if let Some(ports) = sync.get_mut("ports").and_then(Value::as_object_mut) {
        let mut kept = 0;
        ports.retain(|name, value| {
            if !valid_port(name) || kept == MAX_SYNC_PORTS {
                record_reset(resets, "midi_sync.ports (invalid name or too many ports)");
                return false;
            }
            let Some(port) = value.as_object_mut() else {
                record_reset(resets, &format!("midi_sync.ports.{name}"));
                return false;
            };
            kept += 1;
            port.retain(|key, value| {
                let valid = serde_json::from_value::<MidiSyncPort>(serde_json::json!({(key):value}))
                    .is_ok_and(|port| valid_saved_offset(port.offset_samples));
                if !valid { record_reset(resets, &format!("midi_sync.ports.{name}.{key}")); }
                valid
            });
            true
        });
    }
}

fn reset_invalid(
    fields: &mut serde_json::Map<String, serde_json::Value>,
    key: &str,
    path: &str,
    valid: impl FnOnce(&serde_json::Value) -> bool,
    resets: &mut Vec<String>,
) {
    if fields.get(key).is_some_and(|value| !valid(value)) {
        fields.remove(key);
        record_reset(resets, path);
    }
}

fn record_reset(resets: &mut Vec<String>, path: &str) {
    // A corrupt file can have thousands of invalid entries. Keep the status line readable.
    match resets.len() {
        0..8 => resets.push(path.chars().take(160).collect()),
        8 => resets.push("…".into()),
        _ => {}
    }
}

const MAX_UI_BYTES: u64''')
rewrite(p,'    let state: soundcraft_ui_egui::UiState = serde_json::from_value(saved)', '''    let mut resets = Vec::new();
    if let Some(fields) = saved.as_object_mut() {
        recover_sync_settings(fields, &mut resets);
    }
    let mut state: soundcraft_ui_egui::UiState = serde_json::from_value(saved)''')
rewrite(p,'    Ok(Some(state))','''    if !resets.is_empty() {
        let label = state.language.text("A MIDI sync setting could not be read and was reset");
        state.status = format!("{label}: {}", resets.join(", "));
    }
    Ok(Some(state))''')
