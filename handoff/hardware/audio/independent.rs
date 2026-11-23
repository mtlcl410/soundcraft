use asio_sys::{Asio,AsioSampleType};
use std::{env,path::Path,time::Duration};
fn main(){
    let args:Vec<_>=env::args().collect();
    if args.len()!=4 || env::var_os("SOUNDCRAFT_ACCEPTANCE_RUN").is_none() || env::var_os("SC_ASIO_EVIDENCE").is_none(){eprintln!("Usage inside environment.py: independent SAMPLE_RATE BUFFER PCM16LE_MONO_RAW");std::process::exit(2)}
    let sr:i32=args[1].parse().unwrap();let n:i32=args[2].parse().unwrap();
    assert!([44100,48000].contains(&sr)&&[128,256,512].contains(&n));
    let raw=std::fs::read(Path::new(&args[3])).unwrap();assert_eq!(raw.len()%2,0);
    let pcm:Vec<i16>=raw.chunks_exact(2).map(|b|i16::from_le_bytes([b[0],b[1]])).collect();
    assert!(pcm.iter().all(|s|s.unsigned_abs()<=8192));
    let a=Asio::new();let dev=a.load_driver("Model Mixer ASIO").unwrap();
    dev.set_sample_rate(sr as f64).unwrap();
    let channels=dev.channels().unwrap();assert!(channels.ins>=10 && channels.outs>=2);
    let a=dev.prepare_input_stream(None,channels.ins as usize,Some(n)).unwrap();
    let b=dev.prepare_output_stream(a.input,2,Some(n)).unwrap();
    let outputs=b.output.unwrap();assert_eq!(outputs.buffer_size,n);
    let format=dev.output_data_type().unwrap();
    assert!(matches!(format,AsioSampleType::ASIOSTInt32LSB|AsioSampleType::ASIOSTInt24LSB|AsioSampleType::ASIOSTInt16LSB|AsioSampleType::ASIOSTFloat32LSB|AsioSampleType::ASIOSTInt32LSB24));
    let ptrs:Vec<[usize;2]>=outputs.buffer_infos.iter().map(|v| {let [p,q]=v.buffers;[p as usize,q as usize]}).collect();
    let total=pcm.len();let mut i=0;
    let cb=dev.add_callback(move |info|{
        for buffers in &ptrs {
            let p=buffers[info.buffer_index as usize] as *mut u8;
            for j in 0..n as usize {
                let v=pcm.get(i+j).copied().unwrap_or(0) as i32;
                unsafe{match format{
                    AsioSampleType::ASIOSTInt32LSB=>p.cast::<i32>().add(j).write_unaligned(v<<16),
                    AsioSampleType::ASIOSTInt32LSB24=>p.cast::<i32>().add(j).write_unaligned(v<<8),
                    AsioSampleType::ASIOSTInt24LSB=>std::ptr::copy_nonoverlapping((v<<8).to_le_bytes().as_ptr(),p.add(3*j),3),
                    AsioSampleType::ASIOSTInt16LSB=>p.cast::<i16>().add(j).write_unaligned(v as i16),
                    AsioSampleType::ASIOSTFloat32LSB=>p.cast::<f32>().add(j).write_unaligned(v as f32/32768.0),
                    _=>unreachable!(),
                }}
            }
        }
        i+=n as usize;
    });
    dev.start().unwrap();
    std::thread::sleep(Duration::from_secs_f64(total as f64/sr as f64+0.5));
    dev.stop().unwrap();dev.remove_callback(cb);dev.dispose_buffers().unwrap();
    // Give the recorder worker time to flush before process exit.
    std::thread::sleep(Duration::from_millis(300));
}
