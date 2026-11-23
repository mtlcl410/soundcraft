from pathlib import Path
import sys,subprocess
d=Path('..').resolve();c=d/'brake-candidate';s=(c/'new-guard-green.rs').read_text()
f=d/'follow';rf=(f/'crates/ui-egui/src/app/clock_follow/tests/ramp_response.rs').read_text();g=(f/'crates/ui-egui/src/app/clock_follow.rs').read_text()
a=g.index('    #[test]\n    fn two_hours_of_gradual');b=g.index('    #[test]\n    #[ignore',a);dr=g[a:b].rsplit("    }",1)[0]+"    }";s+='\nmod ramps{'+rf+'}\n'+dr
s=s.replace('settling: PulseFit<49>', 'nudge_readout_pulses:u8, settling: PulseFit<49>').replace('settling: Default::default()', 'nudge_readout_pulses:0, settling: Default::default()')
s=s.replace('self.settling.push(ordinal, at);','''self.nudge_readout_pulses=self.nudge_readout_pulses.saturating_sub(1);
        if self.settling.period_us().zip(self.steady.period_us()).is_some_and(|(f,s)| (s-f).abs()>.007*s) {self.nudge_readout_pulses=192;}
        self.settling.push(ordinal,at);'''.replace('>.007','>0.007')).replace('self.phase_tracking() && self.settling.jitter_us() < 950.', 'self.state==State::Locked && self.nudge_readout_pulses>0 && self.settling.jitter_us()<950.')
s=s.replace('phase.abs() > 0.0012','phase.abs() > if s.phase_grid_bpm.is_some() || s.jitter_us>=1. {0.0012} else {0.0026}')
s=s.replace('fn phase_tracking(&self)', '''fn noisy_bend(&self)->bool{
        self.steady.is_tempo_ramp() && self.settling.jitter_us()>900. && self.nudge_readout_pulses==0
    }
    fn phase_tracking(&self)''')
s=s.replace('self.phase_pulses_left > 0','self.phase_pulses_left > 0 && !self.noisy_bend()')
if len(sys.argv)>2:
 exec((c/(sys.argv[2]+'.py')).read_text())
k=sys.argv[1];(c/(k+'.rs')).write_text(s);(c/(k+'.rsp')).write_text((c/'new-guard-green.rsp').read_text().replace('new-guard-green',k))
subprocess.run(['E:/soundcraft/tools/rustup/toolchains/stable-x86_64-pc-windows-msvc/bin/rustc.exe','@../brake-candidate/'+k+'.rsp'],check=True)
with (d/'evidence'/(k+'.log')).open('wb') as out: rc=subprocess.run([str(c/(k+'.exe')),'ramps::','two_hours_of_gradual','dj_tempos::','--nocapture','--test-threads=2'],stdout=out,stderr=subprocess.STDOUT).returncode
print(rc)

