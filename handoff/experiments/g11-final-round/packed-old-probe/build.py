from pathlib import Path
import sys
candidate=Path('.')
def read(p):return Path(p).read_text(encoding='utf-8')
s=read(candidate / 'crates/playback/src/clock_follow.rs')
s=s.replace('use crate::sync_input::PulseFit;', '')
s=s[s.index('#[derive'):s.index('/// Musical start')]+ 'struct PreparedResume;\n'+s[s.index('pub(crate) struct Follower'):s.index('    pub(crate) fn arm(')]+s[s.index('    fn push('):s.index('#[cfg(test)]\nmod tests;')]
# The timeout is owned by F69-1. Its conservative group envelope is staged in the
# temporary harness until the lower implementation joins this checkout.
fit=read('crates/playback/src/sync_input.rs'); fit=fit[fit.index('pub struct PulseFit'):fit.index('#[cfg(test)]')]
grid=read(candidate /'crates/ui-egui/src/app/clock_follow.rs')
grid=grid[grid.index('fn update_grid('):grid.index('#[cfg(test)]\nmod tests')]
mock="""
use std::cell::{Cell, RefCell};
use soundcraft_time::{SampleRate,TempoMap,TICKS_PER_QUARTER};
const TICKS_PER_PULSE:i64=TICKS_PER_QUARTER / 24;
struct MidiInputs{feed:Feed}
struct Feed{time:Cell<i64>,f:RefCell<Follower>}
impl MidiInputs{
 fn with_port_names(_:Vec<String>,_:Vec<String>)->Self{Self{feed:Feed{time:Cell::new(0),f:RefCell::new(Follower::default())}}}
 fn feed(&self)->&Feed {&self.feed}
}
impl Feed{
 fn set_clock(&self,t:i64){self.time.set(t);}
 fn receive(&self,_:u8,b:&[u8]){self.f.borrow_mut().receive(b,self.time.get());}
 fn ports(&self)->&Self{self}
 fn assign(&self,_:&str)->u8{0}
 fn set_clock_follow(&self,_:Option<u8>,coast:bool,_:i64,_:bool){self.f.borrow_mut().coast=coast;}
 fn clock_follow_status(&self,act:&mut Vec<Action>)->Snapshot{let mut f=self.f.borrow_mut();f.expire(self.time.get());while let Some(a)=f.take(){act.push(a);}f.snapshot(self.time.get())}
 fn clock_render_tick(&self)->Option<i64>{self.f.borrow().render_through_pulse().map(|p|p*TICKS_PER_PULSE)}
}
"""
mods='\n'.join('mod '+n+' {\n'+read('crates/ui-egui/src/app/clock_follow/tests/'+n+'.rs')+'\n}' for n in ['sampler_song','packet_steps'])
mods=mods.replace('let malformed = hits.iter()', 'if std::env::var_os("DUMP_VOICES").is_some() { eprintln!("VOICES {:?},{}, {} -> {} {:?}",mode,transition, from, to, hits.iter().map(|(t, v)| (*t, v.len())).collect::<Vec<_>>()); }\n    let malformed = hits.iter()')
mods=mods.replace('record(&format!("A4-{name}"), &r, 28_800);', 'record(&format!("A4-{name}"), &r, 28_800); eprintln!("A4_ERR {name} {:?}",r.attacks.iter().zip(&r.wire).enumerate().filter_map(|(k,(v,w))| if v.len()!=1 || (v[0]-w).abs()>1 {Some((k,v,w))}else {None}).take(8).collect::<Vec<_>>());')
out=Path('../packed-old-probe/pcm.rs')
out.write_text('#![allow(dead_code,private_interfaces)]\n'+fit+s+mock+grid+mods,encoding='utf-8')