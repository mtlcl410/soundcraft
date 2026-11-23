from pathlib import Path
s=Path("crates/playback/src/clock_follow.rs").read_text()
s=s[s.index("#[derive"):s.index("/// Musical start")]+ "struct PreparedResume;\n"+s[s.index("mod wire_step;"):s.index("    pub(crate) fn arm(")]+s[s.index("    fn push("):s.index("#[cfg(test)]\nmod tests;")]
s=s.replace("mod wire_step;","mod wire_step {"+Path("crates/playback/src/clock_follow/wire_step.rs").read_text()+"}")
s=s.replace('self.candidate = Some(Candidate', 'if std::env::var_os("EDGE_DEBUG").is_some() {eprintln!("CAND {pulse} old {} recent {recent} fraction{fraction}",prior.prior_period);} self.candidate = Some(Candidate').replace('let start = c.start;', 'if std::env::var_os("EDGE_DEBUG").is_some() {eprintln!("DONE {pulse} from {} delta{delta} n{n} old{} new{new} error{error} step{step}",c.start.0,c.prior.prior_period);} let start = c.start;')
import os
if os.environ.get("EDGE_BYPASS"): s=s.replace("self.edge.observe(ordinal, at, slow, noise, proposed)", "proposed")
s=s.replace("return proposed;",'if std::env::var_os("EDGE_DEBUG").is_some() && proposed.is_some(){eprintln!("PASS {pulse} old{old} prop{proposed:?}");} return proposed;').replace("else { return proposed };",'else {if std::env::var_os("EDGE_DEBUG").is_some() && proposed.is_some() {eprintln!("FALL {pulse} old{old} prop{proposed:?}");} return proposed };')
fit=Path("crates/playback/src/sync_input.rs").read_text();fit=fit[fit.index("pub struct PulseFit"):fit.index("#[cfg(test)]")]
(out:=Path("../edge-probe/probe.rs")).write_text("#![allow(dead_code,private_interfaces)]\n"+fit+s+Path("../edge-probe/edge-test.rs").read_text())
