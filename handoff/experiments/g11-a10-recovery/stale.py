from pathlib import Path
d=Path(__file__).resolve().parent
for n in ['mtc','follow']:
 p=d/n/'crates/playback/src'
 f=p/'mtc.rs';s=f.read_text()
 start=s.index('            self.next =',s.index('send(stamp, &locate'));end=s.index(';',start)+1
 s=s[:start]+s[start:end].replace('self.next =','let next =')+'''
            if recovering && !relaunch {
                self.stale = self.stale.saturating_add(next.saturating_sub(self.next).max(0) as u64);
            }
            self.next = next;'''+s[end:]; f.write_bytes(s.encode())
 f=p/'mtc_sync_output_tests.rs';s=f.read_text().replace('        for (piece, (ms, bytes)) in recovered[1..9]', '        assert_eq!(stats.stale_dropped.load(Relaxed), (group_ms - loss_ms) / 10);\n        for (piece, (ms, bytes)) in recovered[1..9]')
 f.write_bytes(s.encode())
