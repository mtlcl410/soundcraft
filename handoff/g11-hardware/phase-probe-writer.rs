use std::io::Write;
type ProbeRecord = (u64, u64, u64, f64, u32, u32, [f32; 1024]);
fn probe_writer(path: std::path::PathBuf) -> std::sync::mpsc::SyncSender<ProbeRecord> {
    let (tx, rx) = std::sync::mpsc::sync_channel::<ProbeRecord>(256);
    std::thread::spawn(move || {
        let Ok(mut file) = std::fs::File::create_new(path) else { return };
        for (cb, device, utc, pos, seq, n, samples) in rx {
            let mut block = Vec::with_capacity(40+4*n as usize);
            for v in [cb,device,utc] {block.extend(v.to_le_bytes());}
            block.extend(pos.to_le_bytes());block.extend(seq.to_le_bytes());block.extend(n.to_le_bytes());
            for v in &samples[..n as usize] {block.extend(v.to_le_bytes());}
            if file.write_all(&block).is_err() {break;}
        }
    });
    tx
}
fn utc_ns() -> u64 { std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_nanos() as u64 }
