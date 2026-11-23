"""Optional in-process input tap for a single-client ASIO driver. Only used in the local test build."""
from pathlib import Path
here=Path(__file__).resolve().parent
tree=here.parent.parent/'g11-direct-asio-follow'
p=tree/'crates/playback/src/record.rs';s=p.read_text(encoding='utf8')
marker='    let mut owed = 0;\n    device.build_input_stream('
assert s.count(marker)==1
s=s.replace(marker,'''    let mut owed = 0;
    let mut serial = 0_u64;
    let witness = std::env::var_os("SC_ASIO_WITNESS").filter(|_| config.channels == 12).map(|path| {
        let (tx, rx) = std::sync::mpsc::sync_channel::<([u64; 3], [f32; 512])>(256);
        let file=std::fs::File::create(path).unwrap();
        std::thread::spawn(move || {
            use std::io::Write;
            let mut file=std::io::BufWriter::new(file);
            for (meta, samples) in rx {
                for word in meta { file.write_all(&word.to_le_bytes()).unwrap(); }
                for value in samples { file.write_all(&value.to_le_bytes()).unwrap(); }
                file.flush().unwrap();
            }
        }); tx
    });
    device.build_input_stream(''').replace('move |data: &[T], _: &cpal::InputCallbackInfo| {','''move |data: &[T], info: &cpal::InputCallbackInfo| {
            if let Some(sender)=witness.as_ref() {
                serial+=1;
                let stamp=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos() as u64;
                let t=info.timestamp();
                let adc=t.callback.checked_duration_since(t.capture).map_or(0,|d| d.as_nanos() as u64);
                if data.len()==12*256 {
                    let mut samples=[0.0f32;512];
                    for (source,target) in data.chunks_exact(12).zip(samples.chunks_exact_mut(2)) {
                        target[0]=f32::from_sample(source[10]);target[1]=f32::from_sample(source[11]);
                    }
                    let _=sender.try_send(([stamp,adc,serial],samples));
                }
            }''')
p.write_text(s)
p=tree/'crates/ui-egui/src/app/audio.rs';s=p.read_text();marker='        self.player = Some(player);';assert s.count(marker)>=1
s=s.replace(marker,marker+'''
        if std::env::var_os("SC_ASIO_WITNESS").is_some() && self.ui.audio.system.as_deref()==Some("ASIO") {
            self.ensure_input();
        }''',1);p.write_text(s)

