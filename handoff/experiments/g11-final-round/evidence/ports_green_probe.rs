use std::collections::{BTreeMap, BTreeSet};

type Bindings = BTreeMap<String, String>;

/// Return the selection labels and the opaque native IDs to open for each.
fn assign(saved: &Bindings, found: impl IntoIterator<Item = (String, String)>) -> Bindings {
    let found: Vec<_> = found.into_iter().collect();
    // Some drivers report the same opaque ID for multiple logical ports. Opening one
    // by that ID could address its sibling, so keep such destinations unavailable.
    let mut seen_ids = BTreeSet::new();
    let ambiguous_ids: BTreeSet<_> = found.iter().filter_map(|(_, id)| (!seen_ids.insert(id)).then_some(id)).collect();
    let raw_names: BTreeSet<_> = found.iter().map(|(name, _)| name.as_str()).collect();
    let known: BTreeMap<_, _> = saved.iter().map(|(label, id)| (id, label)).collect();
    let mut available = Bindings::new();
    for (name, id) in &found {
        if ambiguous_ids.contains(id) {
            continue;
        }
        let label = if let Some(label) = known.get(id) {
            (*label).clone()
        } else if !saved.contains_key(name) && !available.contains_key(name) {
            name.clone()
        } else {
            // A real device can itself be named "DIN (2)". Reserve its literal name.
            let last = saved.len().saturating_add(available.len()).saturating_add(raw_names.len()).saturating_add(2);
            let Some(label) = (2..=last)
                .map(|n| format!("{name} ({n})"))
                .find(|label| !saved.contains_key(label) && !available.contains_key(label) && !raw_names.contains(label.as_str()))
            else {
                continue;
            };
            label
        };
        available.insert(label, id.clone());
    }
    available
}

fn selected<'a>(available: &'a Bindings, label: &str) -> Result<&'a str, String> {
    available.get(label).map(String::as_str).ok_or_else(|| format!("MIDI output {label} unavailable"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn listed(ports: &[(&str, &str)]) -> Vec<(String, String)> {
        ports.iter().map(|(name, id)| (name.to_string(), id.to_string())).collect()
    }

    #[test]
    fn duplicate_calibrations_reserve_literal_names_and_reject_indistinguishable_ids() {
        let found = listed(&[("DIN", "a"), ("DIN", "b"), ("DIN (2)", "c"), ("unstable", "d"), ("unstable", "d")]);
        let available = assign(&Bindings::new(), found);
        assert_eq!(available, Bindings::from([("DIN".into(), "a".into()), ("DIN (2)".into(), "c".into()), ("DIN (3)".into(), "b".into())]));
    }

    #[test]
    fn duplicate_calibrations_follow_the_saved_endpoints_after_reopen_and_unplug() {
        let both = listed(&[("DIN", "device-a"), ("DIN", "device-b")]);
        let saved = assign(&Bindings::new(), both);
        let offsets = BTreeMap::from([("DIN", 701), ("DIN (2)", 302)]);
        let reopened: Bindings = saved.clone();
        let now = assign(&reopened, listed(&[("DIN", "device-b"), ("DIN", "device-a")]));
        let routed: BTreeMap<_, _> = offsets.iter().map(|(label, offset)| (selected(&now, label).unwrap(), *offset)).collect();
        assert_eq!(routed, BTreeMap::from([("device-a", 701), ("device-b", 302)]));
        let now = assign(&reopened, listed(&[("DIN", "device-b")]));
        assert!(selected(&now, "DIN").unwrap_err().contains("unavailable"));
        assert_eq!(selected(&now, "DIN (2)").unwrap(), "device-b");
    }
}

