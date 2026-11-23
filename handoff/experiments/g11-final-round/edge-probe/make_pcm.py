from pathlib import Path
s=Path("crates/playback/src/clock_follow.rs").read_text()
s=s[s.index("#[derive"):s.index("/// Musical start")]+ "struct PreparedResume;\n"+s[s.index("mod wire_step;"):s.index("    pub(crate) fn arm(")]+s[s.index("    fn push("):s.index("#[cfg(test)]\nmod tests;")]
s=s.replace("mod wire_step;","mod wire_step {"+Path("crates/playback/src/clock_follow/wire_step.rs").read_text()+"}")
s=s.replace('self.candidate = Some(Candidate', 'if std::env::var_os("EDGE_DEBUG").is_some() {eprintln!("CAND {pulse} old {} recent {recent} fraction{fraction}",prior.prior_period);} self.candidate = Some(Candidate').replace('let start = c.start;', 'if std::env::var_os("EDGE_DEBUG").is_some() {eprintln!("DONE {pulse} from {} delta{delta} n{n} old{} new{new} error{error} step{step}",c.start.0,c.prior.prior_period);} let start = c.start;')
fit=Path("crates/playback/src/sync_input.rs").read_text();fit=fit[fit.index("pub struct PulseFit"):fit.index("#[cfg(test)]")]
import os
if os.environ.get("EDGE_BYPASS"): s=s.replace("self.edge.observe(ordinal, at, slow, noise, proposed)", "proposed")
grid=Path("crates/ui-egui/src/app/clock_follow.rs").read_text();grid=grid[grid.index("fn update_grid("):grid.index("#[cfg(test)]\nmod tests")]
mk=Path("../dj-candidate/make.py").read_text(); mock=mk.split('mock="""')[1].split('"""')[0]
mock=mock.replace(" fn clock_render_tick(&self)", " fn clock_delivery(&self)->soundcraft_mix::ClockDelivery { if self.f.borrow().coalesced_render() {soundcraft_mix::ClockDelivery::Coalesced} else {soundcraft_mix::ClockDelivery::Wire} }\n fn clock_render_tick(&self)").replace('fn receive(&self,_:u8,b:&[u8]){self.f.borrow_mut().receive(b,self.time.get());}', 'fn receive(&self,p:u8,b:&[u8]){if p==0 {self.f.borrow_mut().receive(b,self.time.get());}}').replace('fn assign(&self,_:&str)->u8{0}','fn assign(&self,n:&str)->u8{u8::from(n=="other")}')
mods='\n'.join('mod '+n+' {\n'+Path('crates/ui-egui/src/app/clock_follow/tests/'+n+'.rs').read_text()+'\n}' for n in ['sampler_song','dj_render','brake','dj_tempos','packet_steps'])
Path("../edge-probe/pcm.rs").write_text("#![allow(dead_code,private_interfaces)]\n"+fit+s+mock+grid+mods)
