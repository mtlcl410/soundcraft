#[test]
fn malformed_full_frames_captured_on_din_preserve_position_until_a_valid_locate() {
    let cases: &[(u8, &[u8])] = &[
        (0, &[0xf0,0x7f,0x7f,1,1,0,0,2,0,0,0xf7]),
        (0x20, &[0xf0,0x7f,0x7f,0,1,1,0x20,0,10,0,0xf7]),
        (0x20, &[0xf0,0x7f,0x7f,1,1,0x20,0,2,0,0,0xf7]),
    ];
    for &(hour, damaged) in cases {
        let mut reader=Reader::default();
        let previous=Position::decode(hour,0,8,0).unwrap();
        let target=Position::decode(hour,0,2,0).unwrap();
        let locate=|sec| [0xf0,0x7f,0x7f,1,1,hour,0,sec,0,0xf7];
        reader.read(&locate(8),0);
        assert_eq!(reader.take(0),Some(ChaseEvent::Locate(previous)));
        reader.read(damaged,1_000_000);
        assert_eq!(reader.take(1_000_000),None);
        assert!(matches!(reader.tracking(1_000_000),Tracking::Located(p) if p==previous));
        reader.read(&locate(2),1_100_000);
        assert_eq!(reader.take(1_100_000),Some(ChaseEvent::Locate(target)));
        assert!(matches!(reader.tracking(1_100_000),Tracking::Located(p) if p==target));
    }
}
