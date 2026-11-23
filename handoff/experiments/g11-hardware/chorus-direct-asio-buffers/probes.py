from pathlib import Path
import shutil
here=Path(__file__).resolve().parent; tree=here.parent.parent/'g11-direct-asio-follow'/'crates'/'playback'/'src'
for fn in ('record.rs','stream.rs'):
 p=tree/fn;s=p.read_text(encoding='utf8');shutil.copyfile(p,here/(fn+'.before'))
 if fn=='record.rs':
    s=s.replace('[u64; 3]','[u64; 4]').replace('data.len()==12*256','data.len()<=12*256').replace('[stamp,adc,serial]','[stamp,adc,serial,(data.len()/12) as u64]')
 else:
    start=s.index('    device.build_output_stream(')
    s=s[:start]+'''    let mut serial=0_u64;
    let witness=std::env::var_os("SC_OUTPUT_WITNESS").filter(|_| frame==10).map(|path| {
        let (tx,rx)=std::sync::mpsc::sync_channel::<([u64;4],[f32;512])>(512);
        let file=std::fs::File::create(path).unwrap();
        std::thread::spawn(move || {
            use std::io::Write;
            let mut file=std::io::BufWriter::new(file);
            for (meta,block) in rx {
                for v in meta {file.write_all(&v.to_le_bytes()).unwrap();}
                for v in block {file.write_all(&v.to_le_bytes()).unwrap();}
                file.flush().unwrap();
            }
        });
        tx
    });
'''+s[start:]
    mark='                for (o, x) in out.iter_mut().zip(s.iter()) {'
    assert s.count(mark)==1
    s=s.replace(mark,'''                if let Some(tx)=witness.as_ref() {
                    serial+=1;
                    if frames<=256 {
                       let stamp=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos() as u64;
                       let mut wave=[0_f32;512];
                       for (from,to) in s.chunks_exact(10).zip(wave.chunks_exact_mut(2)) { to.copy_from_slice(&from[8..10]); }
                       let _=tx.try_send(([stamp,0,serial,frames as u64],wave));
                    }
                }
'''+mark)
 p.write_text(s,encoding='utf8')

