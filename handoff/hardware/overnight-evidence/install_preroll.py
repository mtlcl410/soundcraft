from pathlib import Path
import sys
w=Path(sys.argv[1]); a=Path(__file__).resolve().parent; src=w/'crates/playback/src'
def repl(p,old,new):
    s=p.read_text();assert s.count(old)==1;p.write_bytes(s.replace(old,new).encode())
repl(src/'lib.rs','pub mod mtc;','pub mod mtc;\nmod mtc_preroll;')
repl(src/'callback.rs','            if anchor.is_some() && !self.playing {','''            let anchor = anchor.filter(|&at| {
                self.playing || presentation.is_none_or(|target| !crate::mtc_preroll::silent_pcm_prefix(&self.session, at, target))
            });
            if anchor.is_some() && !self.playing {''')
s=(a/'silence_replay.rs').read_text()
i=s.index('        // Test oracle');j=s.index('        let len=wave.len()',i);s=s[:i]+s[j:]
(a/'real_preroll_replay.rs').write_text(s)

