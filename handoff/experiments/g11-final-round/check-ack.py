from pathlib import Path
import subprocess,os
d=Path(__file__).resolve().parent
s=(d/'follow/crates/playback/src/sync_output/port_io.rs').read_text()
fixture=(d/'port-ack-test.rs').read_text()
prefix="""#![allow(dead_code)]
use std::time::Instant;
use std::collections::VecDeque;
trait Destination:Send {fn submit(&mut self, at:Instant, bytes:&[u8],retry:bool,stats:&Stats)->Result<(),String>;fn ready(&mut self,c:&mut VecDeque<Vec<u8>>)->Result<bool,String>;fn flush(&mut self);fn busy(&self)->bool;}
trait SyncPort:Send {fn send_at(&mut self,at:Instant,bytes:&[u8])->Result<Instant,String>;}
struct Stats;
impl Stats {fn delivered(&self,_:Instant,_:Instant,_:&[u8],_:bool) {}}
fn raise_delivery_priority(){}
mod port_io{
"""
for name,source,expected in [('red',s,False),('green',s.replace('ack.packets[first..]','ack.packets.get(first..).unwrap_or_default()'),True)]:
 p=d/'evidence'/f'ack-{name}.rs';p.write_text(prefix+source+fixture+'}',encoding='utf8')
 exe=p.with_suffix('.exe')
 cmd=f'call E:\\soundcraft\\tools\\VSBuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat >nul && E:\\soundcraft\\tools\\rustup\\toolchains\\stable-x86_64-pc-windows-msvc\\bin\\rustc.exe --edition=2024 --test --crate-name ack "{p}" -o "{exe}"'
 subprocess.run(cmd,shell=True,check=True)
 res=subprocess.run([str(exe)],capture_output=True)
 (d/'evidence'/f'F69-3-{name}.log').write_bytes(res.stdout+res.stderr)
 assert (res.returncode==0)==expected
(d/'follow/crates/playback/src/sync_output/port_io.rs').write_text(s.replace('ack.packets[first..]','ack.packets.get(first..).unwrap_or_default()')+'\n'+fixture,encoding='utf8')
