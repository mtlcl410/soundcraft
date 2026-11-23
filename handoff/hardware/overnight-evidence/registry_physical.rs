#[test]
fn nightly_public_output_selector_reaches_din_and_excludes_the_daw_sibling() {
    use std::sync::mpsc::channel;
    use std::time::Duration;
    let mut observer=midir::MidiInput::new("G11 exact connector observer").unwrap();
    observer.ignore(midir::Ignore::None);
    let input=observer.ports().into_iter().find(|p|observer.port_name(p).ok().as_deref()==Some("UM-ONE")).unwrap();
    let (tx,rx)=channel();
    let conn=observer.connect(&input,"DIN verification",move|_,m,_|{if m==[0xf8] {let _=tx.send(());}},()).unwrap();
    let registry=Registry::default();
    for (label,n) in [("Model 12 MIDI",64),("MIDIOUT2 (Model 12 MIDI)",0),("Model 12 MIDI",64)] {
        let (mut output,_)=registry.connect(label).unwrap();
        for _ in 0..64 {output.send(&[0xf8]).unwrap();std::thread::sleep(Duration::from_millis(10));}
        std::thread::sleep(Duration::from_millis(200));
        let count=rx.try_iter().count();
        println!("Product output {label}: {count} on DIN; expected {n}");
        assert_eq!(count,n);
    }
    let pinned=registry.opened().unwrap();
    assert_ne!(pinned["Model 12 MIDI"],pinned["MIDIOUT2 (Model 12 MIDI)"]);
    drop(conn);
}

