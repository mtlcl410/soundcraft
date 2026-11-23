from pathlib import Path
import shutil
d=Path(__file__).resolve().parent;t=d.parents[2]/'g11-direct-asio-follow'
p=t/'crates/vst3-host/src/ffi/instance.rs';s=p.read_text();shutil.copyfile(p,d/'instance.rs.orig')
for a,b in [('unsafe { p.setProcessing(1) };','let mark=std::time::Instant::now(); unsafe { p.setProcessing(1) }; soundcraft_dsp::bench_add(1,(mark.elapsed().as_nanos() as u64)<<8);'),('let r = unsafe { p.process(&mut data) };','let mark=std::time::Instant::now(); let r = unsafe { p.process(&mut data) };soundcraft_dsp::bench_add(4,mark.elapsed().as_nanos() as u64);')]:
 assert s.count(a)==1;s=s.replace(a,b)
p.write_bytes(s.encode())
p=t/'crates/playback/src/stream.rs';s=p.read_text().replace('v[2],v[3],frames as u64','v[2],v[3],(v[4]<<12)|(frames as u64)');p.write_bytes(s.encode())

