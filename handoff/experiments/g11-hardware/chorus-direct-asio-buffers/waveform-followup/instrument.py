from pathlib import Path
import shutil
d=Path(__file__).resolve().parent;t=d.parents[2]/'g11-direct-asio-follow'
def edit(name,changes):
 p=t/name;s=p.read_text();bak=d/(p.parent.parent.name+'-'+p.name+'.orig')
 assert not bak.exists();shutil.copyfile(p,bak)
 for old,new in changes:
    assert s.count(old)==1,(name,old,s.count(old));s=s.replace(old,new)
 p.write_bytes(s.encode())
edit('crates/dsp/src/lib.rs',[('pub mod biquad;', '''std::thread_local! { pub static BENCH: std::cell::Cell<[u64;5]> = const {std::cell::Cell::new([0;5])}; }
pub fn bench_add(i:usize,n:u64){ BENCH.with(|c|{let mut v=c.get();v[i]+=n;c.set(v);}); }
pub mod biquad;''')])
edit('crates/vst3-host/src/plugin.rs',[('            let r = self.inst.process(ProcessInput {','            let bt=std::time::Instant::now();\n            let r = self.inst.process(ProcessInput {'),('            self.pending.clear();\n            self.notes.drain','            soundcraft_dsp::bench_add(0,bt.elapsed().as_nanos() as u64);soundcraft_dsp::bench_add(1,1);\n            self.pending.clear();\n            self.notes.drain')])
edit('crates/playback/src/callback.rs',[('        self.mix.render(&self.session, self.pos, n, &mut self.pending);','        let bt=std::time::Instant::now(); self.mix.render(&self.session, self.pos, n, &mut self.pending); soundcraft_dsp::bench_add(2,bt.elapsed().as_nanos() as u64);'),('        self.drain();\n        self.follow_mtc();','        let bt=std::time::Instant::now(); self.drain(); self.follow_mtc(); soundcraft_dsp::bench_add(3,bt.elapsed().as_nanos() as u64);')])
edit('crates/playback/src/stream.rs',[('    let mut serial=0_u64;', '''    let prof=std::env::var_os("SC_PROF").filter(|_| frame==10).map(|path|{
        let (tx,rx)=std::sync::mpsc::sync_channel::<[u64;8]>(16384);let file=std::fs::File::create(path).unwrap();
        std::thread::spawn(move||{use std::io::Write;let mut file=std::io::BufWriter::new(file);for row in rx{for n in row{file.write_all(&n.to_le_bytes()).unwrap();}}});tx
    });
    let mut serial=0_u64;'''),('                guarded_block(', '                soundcraft_dsp::BENCH.with(|c| c.set([0;5]));let begin=std::time::Instant::now();\n                guarded_block('),('                if let Some(tx)=witness.as_ref() {','''                for (o, x) in out.iter_mut().zip(s.iter()) { *o = output_sample(*x); }
                if let Some(tx)=witness.as_ref() {'''),('for (from,to) in s.chunks_exact(10).zip(wave.chunks_exact_mut(2)) { to.copy_from_slice(&from[8..10]); }','for (from,to) in out.chunks_exact(10).zip(wave.chunks_exact_mut(2)) { to[0]=f32::from_sample(from[8]);to[1]=f32::from_sample(from[9]); }'),('                for (o, x) in out.iter_mut().zip(s.iter()) {\n                    *o = output_sample(*x);\n                }','''                if let Some(tx)=prof.as_ref(){let v=soundcraft_dsp::BENCH.with(|c|c.get());let now=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos() as u64;let _=tx.try_send([serial,now,begin.elapsed().as_nanos() as u64,v[0],v[1],v[2],v[3],frames as u64]);}''')])

