use cpal::traits::{DeviceTrait,HostTrait,StreamTrait};
include!("E:/soundcraft/compatibility-audit/g11-hardware/phase-probe-writer.rs");
fn main() -> Result<(),Box<dyn std::error::Error>> {
    let path=std::env::args().nth(1).ok_or("capture file required")?;
    let stop=std::path::PathBuf::from(format!("{path}.stop"));
    let device=cpal::default_host().output_devices()?.find(|d|d.description().is_ok_and(|i|i.name().contains("(High Definition Audio Device)")&&!i.name().contains("S/PDIF"))).ok_or("loopback output missing")?;
    let cfg=device.default_output_config()?;
    assert_eq!(cfg.sample_rate(),48000);
    assert_eq!(cfg.sample_format(),cpal::SampleFormat::F32);
    let ch=cfg.channels() as usize;
    let tx=probe_writer(path.into());
    let mut seq=0;
    let stream=device.build_input_stream(cfg.config(),move |data:&[f32],info:&cpal::InputCallbackInfo|{
        let stamp=info.timestamp();
        let utc=utc_ns();
        for (i, sub) in data.chunks(1024*ch).enumerate() {
            let n=sub.len()/ch;
            let mut s=[0.0;1024];
            for (out,v) in s.iter_mut().zip(sub.chunks_exact(ch)) {*out=v.iter().sum::<f32>()/ch as f32;}
            let off=(i as u64*1024)*1_000_000_000/48000;
            let _=tx.try_send((stamp.callback.as_nanos() as u64,stamp.capture.as_nanos() as u64+off,utc,0.,seq,n as u32,s));
            seq+=1;
        }
    },|e| eprintln!("{e}"),None)?;
    stream.play()?;
    println!("READY");
    let start=std::time::Instant::now();
    while !stop.exists() && start.elapsed().as_secs()<900 {std::thread::sleep(std::time::Duration::from_millis(100));}
    drop(stream);
    std::thread::sleep(std::time::Duration::from_millis(200));
    Ok(())
}
