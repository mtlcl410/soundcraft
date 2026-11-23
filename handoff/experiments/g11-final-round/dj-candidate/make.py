from pathlib import Path
import sys
candidate=Path('../dj-candidate')
def read(p):return Path(p).read_text(encoding='utf-8')
s=read(candidate / 'crates/playback/src/clock_follow.rs')
s=s.replace('use crate::sync_input::PulseFit;', '')
s=s[s.index('#[derive'):s.index('/// Musical start')]+ 'struct PreparedResume;\n'+s[s.index('struct WireStep'):s.index('    pub(crate) fn arm(')]+s[s.index('    fn push('):s.index('#[cfg(test)]\nmod tests;')]
fit=read(candidate/'crates/playback/src/sync_input.rs'); fit=fit[fit.index('pub struct PulseFit'):fit.index('#[cfg(test)]')]
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
mods='\n'.join('mod '+n+' {\n'+read('crates/ui-egui/src/app/clock_follow/tests/'+n+'.rs')+'\n}' for n in ['sampler_song','dj_render','brake','dj_tempos'])
ft=read(Path('../brake-candidate')/'crates/playback/src/clock_follow/tests.rs')
ft=ft[:ft.index('#[test]\nfn midi_clock_wakes_only')] + ft[ft.index('#[test]\nfn new_transport_survives'):ft.index('#[test]\nfn failed_prepared')] + ft[ft.index('#[test]\nfn stable_device_prediction'):]
mods += '\nmod unit_tests {\n'+ft+'\n}'
out=candidate/'try.rs'; out.write_text('#![allow(dead_code,private_interfaces)]\n'+fit+s+mock+grid+mods,encoding='utf-8')

