"""Build private diagnostic from saved packets. No compiler hook in product patches."""
from pathlib import Path
import sys
a=Path(__file__).resolve().parent; w=Path(sys.argv[1]); src=w/'crates/playback/src'
r=a.parent/'runs/home-20261123-002520-recorder'
s=(r/'paired.rs').read_text()
s=s.replace('let mut lines=text.lines();','let mut lines=text.lines(); let mut reference=None;')
s=s.replace('let mut s=session(rate);','let mut s=session(rate);')
s=s.replace('let len=wave.len() as i64;',"""// Test oracle derived from the actual input PCM, relative to the stopped locate.
        let anchor_sample = score - 12000;
        let first = wave[anchor_sample..].iter().position(|v| *v != 0.).unwrap() + anchor_sample;
        crate::callback::TEST_SILENCE_END.with(|cell| cell.set(first as i64));
        let len=wave.len() as i64;""")
start=s.index('println!("PAIR,')
s=s[:start]+'''println!("PAIR,{},{},{},{partial},{hits:?}",h[0],h[1],onset.unwrap());
        assert_eq!(partial,0);
        if h[1]=="rolling" { reference=onset; }
        else {
            assert!(onset.unwrap().abs_diff(reference.unwrap()) <= 21, "stopped locate changes first onset by {} us", onset.unwrap()-reference.unwrap());
        }
        assert_eq!(hits,[1;16]);
    }
}
'''
(a/'silence_replay.rs').write_text(s,encoding="utf-8")
p=src/'mtc/tests.rs'
p.write_bytes((p.read_text()+'\n#[cfg(test)]\nmod silent_lead_replay { include!(r"'+str(a/'silence_replay.rs')+'"); }\n').encode())
p=src/'callback.rs'
s=p.read_text()
i=s.index('        if !self.chasing || !self.playing {',s.index('let source_seek ='))
idx=s.index('            if anchor.is_some()',i)
s=s[:idx]+'''            #[cfg(test)]
            let anchor = anchor.filter(|at| !TEST_SILENCE_END.with(|bound| {
                presentation.is_some_and(|live| live > *at && live <= bound.get()) && TEST_SILENT_PREROLL.with(|opt| opt.get())
            }));
'''+s[idx:]
s+='''

#[cfg(test)]
thread_local! {
    pub(crate) static TEST_SILENCE_END: std::cell::Cell<i64> = const { std::cell::Cell::new(-1) };
    pub(crate) static TEST_SILENT_PREROLL: std::cell::Cell<bool> = std::cell::Cell::new(std::env::var_os("SC_TEST_SILENT_PREFIX").is_some());
}
'''
p.write_bytes(s.encode())

