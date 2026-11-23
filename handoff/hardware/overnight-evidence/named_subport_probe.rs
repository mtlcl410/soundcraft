// Local hardware probe: verify that exact (opaque ID, name) can address both
// logical WinMM endpoints even when find_port_by_id alone cannot distinguish them.
#[test]
fn exact_native_pair_reaches_only_the_physical_din_connector() {
    use std::sync::mpsc::channel;
    use std::time::{Duration, Instant};
    let mut input=midir::MidiInput::new("G11 receive").unwrap();
    input.ignore(midir::Ignore::None);
    let dest=input.ports().into_iter().find(|p|input.port_name(p).ok().as_deref()==Some("UM-ONE")).unwrap();
    let (tx,rx)=channel::<Instant>();
    let reader=input.connect(&dest,"G11 witness",move|_,bytes,_|{if bytes==[0xf8] {let _=tx.send(Instant::now());}},()).unwrap();
    let mut previous_id=None;
    for (name,expected) in [("Model 12 MIDI",64),("MIDIOUT2 (Model 12 MIDI)",0),("Model 12 MIDI",64)] {
        let output=midir::MidiOutput::new("G11 exact endpoint").unwrap();
        let ports=output.ports();
        let exact: Vec<_>=ports.iter().filter(|p|output.port_name(p).ok().as_deref()==Some(name)).collect();
        assert_eq!(exact.len(),1);
        let id=exact[0].id();
        assert!(ports.iter().filter(|p|p.id()==id).count()>=2);
        if let Some(old)=&previous_id {assert_eq!(old,&id);}
        previous_id=Some(id);
        let mut connection=output.connect(exact[0],"G11 exact endpoint").unwrap();
        for _ in 0..64 {connection.send(&[0xf8]).unwrap();std::thread::sleep(Duration::from_millis(10));}
        std::thread::sleep(Duration::from_millis(200));drop(connection);
        let count=rx.try_iter().count();
        println!("Exact endpoint {name}: {count}/64 reached UM-ONE, expected {expected}");
        assert_eq!(count,expected);
    }
    drop(reader);
}

