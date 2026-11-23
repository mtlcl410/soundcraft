from pathlib import Path
import sys
candidate=Path('../brake-candidate')
def read(p):return Path(p).read_text(encoding='utf-8')
s=read(candidate / 'crates/playback/src/clock_follow.rs')
s=s.replace('use crate::sync_input::PulseFit;', '')
s=s[s.index('#[derive'):s.index('/// Musical start')]+ 'struct PreparedResume;\n'+s[s.index('pub(crate) struct Follower'):s.index('    pub(crate) fn arm(')]+s[s.index('    fn push('):s.index('#[cfg(test)]\nmod tests;')]
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
 fn receive(&self,port:u8,b:&[u8]){if port==0 { self.f.borrow_mut().receive(b,self.time.get()); }}
 fn ports(&self)->&Self{self}
 fn assign(&self,name:&str)->u8{u8::from(name=="other")}
 fn set_clock_follow(&self,_:Option<u8>,coast:bool,_:i64,_:bool){self.f.borrow_mut().coast=coast;}
 fn clock_follow_status(&self,act:&mut Vec<Action>)->Snapshot{let mut f=self.f.borrow_mut();f.expire(self.time.get());while let Some(a)=f.take(){act.push(a);}f.snapshot(self.time.get())}
 fn clock_render_tick(&self)->Option<i64>{self.f.borrow().render_through_pulse().map(|p|p*TICKS_PER_PULSE)}
}
"""
mods='\n'.join('mod '+n+' {\n'+read('crates/ui-egui/src/app/clock_follow/tests/'+n+'.rs')+'\n}' for n in ['sampler_song','dj_render','brake','dj_tempos'])
ft=read(candidate/'crates/playback/src/clock_follow/tests.rs')
ft=ft[:ft.index('#[test]\nfn midi_clock_wakes_only')] + ft[ft.index('#[test]\nfn new_transport_survives'):ft.index('#[test]\nfn failed_prepared')] + ft[ft.index('#[test]\nfn stable_device_prediction'):]
mods += '\nmod unit_tests {\n'+ft+'\n}'
mods=mods.replace('(base + 48) / 12','(base + 24) / 12')
mods=mods.replace('let x = &signed[cut / 12..];','assert!(r.snapshots.iter().all(|s| !s.braking), "{name}: step classified as brake");\n                let x = &signed[cut / 12..];')
out=candidate/'pcm_probe.rs'; out.write_text('#![allow(dead_code,private_interfaces)]\n'+fit+s+mock+grid+mods,encoding='utf-8')
base=Path('E:/soundcraft/compatibility-audit/g11-follow-r3-target/debug/build')
dirs=set(p.parent for p in base.glob('*/*/out/*.rlib'))|set(p.parent for p in base.glob('*/*/out/*.lib'))|set(p.parent for p in base.glob('*/*/out/*.dll'))|set(p.parent for p in base.glob('*/*/out/**/*.lib'))
args=['--edition=2024','--test',str(out),'-o',str(candidate/'pcm_probe.exe')]
args += ['-L'+str(d.absolute()) for d in dirs]
for name in ['soundcraft_mix','soundcraft_model','soundcraft_midi','soundcraft_time','craft_audio']:
 libs=sorted(base.glob(name.replace('_','-')+'/*/out/lib'+name+'-*.rlib'),key=lambda p:p.stat().st_mtime,reverse=True)
 args+=['--extern', name+'='+str(libs[0].absolute())]
(candidate/'pcm.rsp').write_text('\n'.join(args),encoding='utf-8')
