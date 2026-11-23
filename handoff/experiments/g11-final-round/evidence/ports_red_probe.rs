use std::collections::{BTreeMap, BTreeSet};

type Bindings = BTreeMap<String, String>;

/// Return the selection labels and the opaque native IDs to open for each.
fn assign(_saved: &Bindings, found: impl IntoIterator<Item = (String, String)>) -> Bindings {
    let mut available = Bindings::new();
    for (name,id) in found {available.entry(name).or_insert(id);}
    available
}

fn selected<'a>(available: &'a Bindings, label: &str) -> Result<&'a str,String> {
    available.get(label).map(String::as_str).ok_or_else(|| format!("MIDI output {label} unavailable"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn listed(ports: &[(&str,&str)]) -> Vec<(String,String)> {
        ports.iter().map(|(name,id)| (name.to_string(),id.to_string())).collect()
    }

    #[test]
    fn duplicate_calibrations_follow_the_saved_endpoints_after_reopen_and_unplug() {
        let both = listed(&[("DIN","device-a"),("DIN","device-b")]);
        let saved=assign(&Bindings::new(),both);
        let offsets=BTreeMap::from([("DIN",701),("DIN (2)",302)]);
        let reopened: Bindings=saved.clone();
        let now=assign(&reopened,listed(&[("DIN","device-b"),("DIN","device-a")]));
        let routed: BTreeMap<_,_> = offsets.iter().map(|(label, offset)|(selected(&now,label).unwrap(),*offset)).collect();
        assert_eq!(routed,BTreeMap::from([("device-a",701),("device-b",302)]));
        let now=assign(&reopened,listed(&[("DIN","device-b")]));
        assert!(selected(&now,"DIN").unwrap_err().contains("unavailable"));
        assert_eq!(selected(&now,"DIN (2)").unwrap(),"device-b");
    }
}

