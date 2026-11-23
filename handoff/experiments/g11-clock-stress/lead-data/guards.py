from pathlib import Path
d=Path('E:/soundcraft/compatibility-audit/g11-clock-stress/lead-fix/crates/playback/src/clock_follow')
p=d/'render_lead.rs';s=p.read_text().replace('    Predict,\n','    Predict,\n    Expired,\n    Clamped,\n')
s=s.replace('    let mut pulse = 0;','    let mut stream_lead = crate::sync_clock::StreamLead::default();\n    let measured = Duration::from_millis(lead_ms as u64);\n    stream_lead.observe(start,Some(measured));\n    let mut pulse = 0;')
i=s.index('        audio.device_timing =');j=s.index('        audio.fill',i)
s=s[:i]+'''        let callback = start + Duration::from_secs_f64(at as f64 / RATE as f64);
        audio.device_timing = match policy {
            Policy::Hard => None,
            Policy::Expired => Some(DeviceTiming::new(callback - Duration::from_secs(2), Some(measured), 0)),
            Policy::Clamped => Some(stream_lead.observe(callback,None)),
            Policy::Reference | Policy::Predict => Some(DeviceTiming::new(callback,Some(measured),0)),
        };
'''+s[j:]
s+='''
#[test]
fn expired_and_clamped_device_timestamps_keep_the_hard_horizon() {
    for clicks in [true,false] {
        let hard=render(300,1500,50,clicks,Policy::Hard);
        assert_eq!(hard,render(300,1500,50,clicks,Policy::Expired));
        assert_eq!(hard,render(300,1500,50,clicks,Policy::Clamped));
    }
}
'''
p.write_text(s)

