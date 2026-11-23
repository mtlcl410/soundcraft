import os,sys,subprocess
from pathlib import Path
w=Path(__file__).resolve().parent/'follow'
d=w.parent
c=d/'brake-candidate'
def read(x):return x.read_text(encoding='utf8')
def src(x):return read(w/x)
def mod(name,s):return '\nmod '+name+' {\n'+s+'\n}\n'
f=src('crates/playback/src/clock_follow.rs')
f=f[f.index('#[derive'):f.index('/// Musical start')]+'struct PreparedResume;\n'+mod('wire_step',src('crates/playback/src/clock_follow/wire_step.rs'))+f[f.index('pub(crate) struct Follower'):f.index('    pub(crate) fn arm(')]+f[f.index('    fn push('):f.index('#[cfg(test)]\nmod tests;')]
fit=src('crates/playback/src/sync_input.rs');fit=fit[fit.index('pub struct PulseFit'):fit.index('#[cfg(test)]')]
mock=read(c/'steady-final.rs'); mock=mock[mock.index('use std::cell::{Cell, RefCell};'):mock.index('fn update_grid(')]
grid=src('crates/ui-egui/src/app/clock_follow.rs');grid=grid[grid.index('fn update_grid('):grid.index('#[cfg(test)]\nmod tests')]
s='#![allow(dead_code,private_interfaces)]\n'+fit+f+mock+grid+mod('history',src('crates/ui-egui/src/app/clock_follow/history.rs'))
for name in ['sampler_song','dj_render','packet_steps','dj_tempos','brake','ramp_response','large_steps']:
    s+=mod(name,src('crates/ui-egui/src/app/clock_follow/tests/'+name+'.rs'))
variant=sys.argv[1]
if len(sys.argv)>2:exec(read(d/sys.argv[2]))
rs=c/f'r2-{variant}.rs'; exe=rs.with_suffix('.exe')
rs.write_text(s,encoding='utf8')
args=read(c/'steady-final.rsp').replace('steady-final.rs','r2-'+variant+'.rs').replace('steady-final.exe','r2-'+variant+'.exe').replace('opt-level=1','opt-level=2');rp=rs.with_suffix('.rsp');rp.write_text(args)
result=subprocess.run([r'E:/soundcraft/tools/rustup/toolchains/stable-x86_64-pc-windows-msvc/bin/rustc.exe','@'+str(rp)],cwd=w,capture_output=True,text=True)
print(result.stderr[-4500:]); sys.exit(result.returncode)

