extern crate self as soundcraft_ui_egui;
pub mod midi_sync {
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct MidiSyncPort {
    pub enabled: bool,
    #[serde(alias = "offset_samples")]
    pub out_offset_samples: i64,
    pub in_offset_samples: i64,
}

/// Beat Clock commands only change output routing and calibration.
#[derive(Serialize, Deserialize, Default)]
#[serde(default, deny_unknown_fields)]
pub(crate) struct BeatDestination {
    enabled: bool,
    offset_samples: i64,
}

pub(crate) fn beat_destinations(ports: &BTreeMap<String, MidiSyncPort>) -> BTreeMap<&str, BeatDestination> {
    ports.iter().map(|(name, p)| (name.as_str(), BeatDestination { enabled: p.enabled, offset_samples: p.out_offset_samples })).collect()
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Compensation {
    pub beat_clock: bool,
    pub mtc: bool,
    pub notes: bool,
}

impl Default for Compensation {
    fn default() -> Self {
        Self { beat_clock: true, mtc: true, notes: false }
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct MidiSync {
    pub enabled: bool,
    pub ports: BTreeMap<String, MidiSyncPort>,
    /// Saved device IDs keep same-name occurrence labels stable across restart and unplug.
    #[serde(skip_serializing_if = "BTreeMap::is_empty")]
    pub port_ids: BTreeMap<String, String>,
    pub compensation: Compensation,
}

pub const MAX_SYNC_PORTS: usize = 256;
/// Before input and output calibration shared a table, each list could fill independently.
pub const MAX_SAVED_SYNC_PORTS: usize = 2 * MAX_SYNC_PORTS;

pub fn valid_saved_offset(samples: i64) -> bool {
    samples.unsigned_abs() <= 10_000_000
}

pub fn valid_port(name: &str) -> bool {
    !name.trim().is_empty() && name.len() <= 1024
}

}
fn recover_sync_settings(fields: &mut serde_json::Map<String, serde_json::Value>, resets: &mut Vec<String>) {
    use serde_json::Value;
    use soundcraft_ui_egui::midi_sync::{Compensation, MAX_SAVED_SYNC_PORTS, MAX_SYNC_PORTS, MidiSyncPort, valid_port, valid_saved_offset};

    reset_invalid(fields, "gen_mtc", "gen_mtc", Value::is_boolean, resets);
    for port in ["mtc_input_port", "mtc_output_port", "clock_follow_input"] {
        reset_invalid(fields, port, port, |v| v.is_null() || v.as_str().is_some_and(valid_port), resets);
    }
    reset_invalid(fields, "clock_follow_stop_on_loss", "clock_follow_stop_on_loss", Value::is_boolean, resets);
    reset_invalid(fields, "clock_follow_input_offsets", "clock_follow_input_offsets", Value::is_object, resets);
    if let Some(offsets) = fields.get_mut("clock_follow_input_offsets").and_then(Value::as_object_mut) {
        let mut kept = 0;
        offsets.retain(|name, value| {
            if kept == MAX_SYNC_PORTS || !valid_port(name) || !value.as_i64().is_some_and(valid_saved_offset) {
                record_reset(resets, &format!("clock_follow_input_offsets.{name}"));
                return false;
            }
            kept += 1;
            true
        });
    }
    reset_invalid(fields, "midi_sync", "midi_sync", Value::is_object, resets);
    let mtc_output_port = fields.get("mtc_output_port").and_then(Value::as_str).map(str::to_owned);
    let Some(sync) = fields.get_mut("midi_sync").and_then(Value::as_object_mut) else { return };
    reset_invalid(sync, "enabled", "midi_sync.enabled", Value::is_boolean, resets);
    reset_invalid(sync, "compensation", "midi_sync.compensation", Value::is_object, resets);
    if let Some(compensation) = sync.get_mut("compensation").and_then(Value::as_object_mut) {
        compensation.retain(|key, value| {
            let valid = serde_json::from_value::<Compensation>(serde_json::json!({(key):value})).is_ok();
            if !valid {
                record_reset(resets, &format!("midi_sync.compensation.{key}"));
            }
            valid
        });
    }
    reset_invalid(sync, "ports", "midi_sync.ports", Value::is_object, resets);
    if let Some(ports) = sync.get_mut("ports").and_then(Value::as_object_mut) {
        let mut kept = 0;
        ports.retain(|name, value| {
            if !valid_port(name) || kept == MAX_SAVED_SYNC_PORTS {
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
                    .is_ok_and(|port| valid_saved_offset(port.out_offset_samples) && valid_saved_offset(port.in_offset_samples));
                if !valid {
                    record_reset(resets, &format!("midi_sync.ports.{name}.{key}"));
                }
                valid
            });
            // Keep the canonical output calibration if the file also contains its legacy alias.
            if port.contains_key("out_offset_samples") && port.remove("offset_samples").is_some() {
                record_reset(resets, &format!("midi_sync.ports.{name}.offset_samples"));
            }
            true
        });
    }
    reset_invalid(sync, "port_ids", "midi_sync.port_ids", Value::is_object, resets);
    let binding_limit = sync.get("ports").and_then(Value::as_object).map_or(MAX_SYNC_PORTS, |ports| ports.len().max(MAX_SYNC_PORTS));
    if let Some(ids) = sync.get_mut("port_ids").and_then(Value::as_object_mut) {
        let mut kept = 0;
        ids.retain(|name, value| {
            // A zero-offset MTC-only destination has an identity without occupying a calibration slot.
            let calibration_slot = mtc_output_port.as_deref() != Some(name.as_str());
            if !valid_port(name) || (calibration_slot && kept == binding_limit) || !value.as_str().is_some_and(valid_port) {
                record_reset(resets, &format!("midi_sync.port_ids.{name}"));
                return false;
            }
            kept += usize::from(calibration_slot);
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

fn main() {
 let mut ports=serde_json::Map::new();let mut ids=serde_json::Map::new();
 for i in 0..256 {
   ports.insert(format!("A Input {i}"),serde_json::json!({"in_offset_samples":1}));
   ports.insert(format!("Z Output {i}"),serde_json::json!({"enabled":true,"out_offset_samples":2}));
   ids.insert(format!("Z Output {i}"),serde_json::json!(format!("native-{i}")));
 }
 ids.insert("ZZ MTC only".into(),serde_json::json!("generator-id"));
 let mut fields=serde_json::json!({"midi_sync":{"ports":ports,"port_ids":ids},"mtc_output_port":"ZZ MTC only"});
 let mut resets=Vec::new();
 recover_sync_settings(fields.as_object_mut().unwrap(),&mut resets);
 let port=fields["midi_sync"]["ports"].as_object().unwrap();let ids=fields["midi_sync"]["port_ids"].as_object().unwrap();
 println!("saved 256 input + 256 output, recovered {} inputs {} outputs; {}/257 identities, MTC={}; resets={:?}",port.keys().filter(|key|key.starts_with("A Input")).count(),port.keys().filter(|key|key.starts_with("Z Output")).count(),ids.len(),ids["ZZ MTC only"],resets);
 assert_eq!(port.len(),512);
}
