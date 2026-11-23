from pathlib import Path
import sys
base=Path('crates/playback/src')
def read(p):return Path(p).read_text(encoding='utf-8')
s=read(sys.argv[1])
s=s.replace('use crate::sync_input::PulseFit;', '')
s=s[s.index('#[derive'):s.index('/// Musical start')]+ 'struct PreparedResume;\n'+s[s.index('pub(crate) struct Follower'):s.index('    pub(crate) fn arm(')]+s[s.index('    fn push('):s.index('#[cfg(test)]\nmod tests;')]
fit=read(base/'sync_input.rs')
fit=fit[fit.index('pub struct PulseFit'):fit.index('#[cfg(test)]')]
test="""
fn main(){
 for l in [24usize,48] {for exp in [false,true]{
  let mut f=Follower::default(); let mut now=0.; let cut=192; let b=cut+l+24;
  f.receive(&[0xfa],0);
  for p in 0..b+120 {
   f.receive(&[0xf8],now as i64);let s=f.snapshot(now as i64);
   if p>=cut&&p<=b+48&&(p%6==0||s.state!=State::Locked){println!("{l} {exp} p={p} bpm={:?} {state:?} braking={brake} cap={:?}",s.bpm,f.render_through_pulse(), state=s.state,brake=BRAKE);}
   let bpm=if p<cut {128.}else if p<cut+l {let a=(p-cut+1) as f64/l as f64; if exp{128.*(5f64/128.).powf(a)}else{128.-123.*a}}else if p<b{5.}else{5.+123.*(((p-b+1)as f64/24.).min(1.))};
   let nt=now+2_500_000./bpm;
   let mut t=now+1000.;while t<nt{f.expire(t as i64);t+=1000.;}
   now=nt;
  }
 }}
}
""".replace('BRAKE','f.brake_pulses_left' if 'brake_pulses_left' in s else '0')
Path('../brake-candidate/probe.rs').write_text('#![allow(dead_code,private_interfaces)]\n'+fit+s+test,encoding='utf-8')
