from pathlib import Path
import sys
p=Path(sys.argv[1])/'crates/playback/src/sync_output/ports.rs';s=p.read_text()
s=s.replace('use midir::{MidiOutput, MidiOutputConnection};','use midir::{MidiOutput, MidiOutputConnection, MidiOutputPort};')
old='''fn scan(midi: &MidiOutput, saved: &Bindings) -> Bindings {
    assign(saved, midi.ports().iter().map(|port| (midi.port_name(port).ok(), port.id())))
}'''
new='''type PortNames = Vec<(Option<String>, String)>;

// WinMM gives logical ports on the same USB interface the same opaque ID.
// midir opens an enumerated WinMM object by checking both its name and
// interface ID again. Keep indistinguishable and partially named groups closed.
#[cfg(any(windows, test))]
fn winmm_names(mut ports: PortNames, saved: &Bindings) -> PortNames {
    let mut groups = BTreeMap::new();
    for (name, id) in &ports {
        let group = groups.entry(id.clone()).or_insert((0usize, true));
        group.0 += 1;
        group.1 &= name.is_some();
    }
    let pinned: BTreeSet<_> = saved.values().collect();
    for (name, id) in &mut ports {
        let Some(label) = name else { continue };
        let (count, fully_named) = groups[id];
        if !fully_named || id.is_empty() {
            continue;
        }
        let pair = format!("winmm-port:{}:{id}{label}", id.len());
        if count > 1 || pinned.contains(&pair) {
            *id = pair;
        }
    }
    ports
}

fn enumerate(midi: &MidiOutput, saved: &Bindings) -> (Vec<MidiOutputPort>, PortNames) {
    let ports = midi.ports();
    let names = ports.iter().map(|p| (midi.port_name(p).ok(), p.id())).collect();
    #[cfg(windows)]
    let names = winmm_names(names, saved);
    #[cfg(not(windows))]
    let _ = saved;
    (ports, names)
}'''
assert old in s;s=s.replace(old,new).replace('Ok(scan(&midi, saved))','Ok(assign(saved, enumerate(&midi, saved).1))')
old='''    let ids = scan(&midi, saved);
    let id = selected(&ids, label)?;
    let port = midi.find_port_by_id(id).ok_or_else(|| format!("MIDI output {label} unavailable"))?;
    let conn = midi.connect(&port, "SoundCraft MIDI sync").map_err(|e| e.to_string())?;'''
new='''    let (ports, names) = enumerate(&midi, saved);
    let ids = assign(saved, names.iter().cloned());
    let id = selected(&ids, label)?;
    let index = names.iter().position(|(_, key)| key == id).ok_or_else(|| format!("MIDI output {label} unavailable"))?;
    let conn = midi.connect(&ports[index], "SoundCraft MIDI sync").map_err(|e| e.to_string())?;'''
assert old in s;s=s.replace(old,new)
idx=s.index('    #[test]\n',s.index('mod tests {'))
s=s[:idx]+'''    #[test]
    fn named_winmm_subports_keep_their_exact_connector_across_reorder_and_partial_disconnect() {
        let raw = listed(&[("DIN", "usb"), ("DAW", "usb"), ("Other", "other")]);
        let names = winmm_names(raw.clone(), &Bindings::new());
        let saved = assign(&Bindings::new(), names);
        assert_ne!(saved["DIN"], saved["DAW"]);
        assert_eq!(saved["Other"], "other");
        let mut reversed = raw;
        reversed.reverse();
        assert_eq!(assign(&saved, winmm_names(reversed, &saved)), saved);
        let single = assign(&saved, winmm_names(listed(&[("DAW", "usb")]), &saved));
        assert_eq!(single.get("DAW"), saved.get("DAW"));
        assert!(!single.contains_key("DIN"));
        let legacy = Bindings::from([("DIN".into(), "usb".into())]);
        let changed = assign(&legacy, winmm_names(listed(&[("DIN", "usb"), ("DAW", "usb")]), &legacy));
        assert!(!changed.contains_key("DIN")); // a legacy ambiguous ID needs reselection
    }

    #[test]
    fn ambiguous_winmm_names_and_unreadable_siblings_remain_unavailable() {
        let duplicates = winmm_names(listed(&[("DIN", "usb"), ("DIN", "usb")]), &Bindings::new());
        assert!(assign(&Bindings::new(), duplicates).is_empty());
        let unreadable = vec![(Some("DIN".into()), "usb".into()), (None, "usb".into())];
        assert!(assign(&Bindings::new(), winmm_names(unreadable, &Bindings::new())).is_empty());
    }

'''+s[idx:];p.write_bytes(s.encode())

