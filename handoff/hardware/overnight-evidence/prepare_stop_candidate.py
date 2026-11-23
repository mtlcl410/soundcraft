"""Construct local red/green variants in the isolated checkout."""
from pathlib import Path
import re, sys

root = Path(__file__).resolve().parent.parent/'stop-ordinal-local'/'crates/playback/src'
def rep(file, old, new):
    p=root/file
    s=p.read_text()
    assert s.count(old)==1,(file,old)
    p.write_text(s.replace(old,new),newline='\n')

if sys.argv[1]=='red':
    # Compatibility hooks are inert on red. All sends still reach the same native function.
    rep('sync_output.rs','    fn ready(&mut self, _cleanup:', '''    fn submit_beat(&mut self, at: Instant, _pass: u64, stats: &Stats) -> Result<(), String> {
        self.submit(at, &[0xf8], false, stats)
    }
    fn ready(&mut self, _cleanup:''')
    rep('midi.rs','    clock_source: AtomicUsize,','    pub(crate) clock_audio_pass: AtomicU64,\n    clock_source: AtomicUsize,')
    rep('midi.rs','            clock_source: AtomicUsize::','            clock_audio_pass: AtomicU64::new(0),\n            clock_source: AtomicUsize::')
    s=(Path(__file__).parent/'stop_cutoff_tests.rs').read_text()
    s=re.sub(r'feed.receive_at\(0,([^,]+),([^;]+)\);',r'feed.set_clock(\2); feed.receive(0,\1);',s)
    p=root/'sync_output/port_io.rs'
    p.write_text(p.read_text()+s,newline='\n')
else:
    rep('sync_output.rs','struct Stats {','''struct Stats {
    // Published once on a selected source's explicit Stop. Normal F8 delivery
    // needs only the pass comparison; separate destinations retain their own ordinals.
    stopped_pass: AtomicU64,
    stopped_boundary: Mutex<(u64, i64)>,''')
    rep('sync_output.rs','        self.chase_feed = Arc::downgrade(feed);','''        if let Some(old) = self.chase_feed.upgrade() {
            old.set_clock_boundary_listener(None);
        }
        let source = Arc::downgrade(feed);
        let stats = Arc::downgrade(&self.stats);
        feed.set_clock_boundary_listener(Some(Arc::new(move |last| {
            let Some(source) = source.upgrade() else { return };
            let pass = source.clock_audio_pass.swap(0, std::sync::atomic::Ordering::AcqRel);
            if let (Some(last), Some(stats)) = (last, stats.upgrade()) && pass != 0 {
                *stats.stopped_boundary.lock().unwrap_or_else(std::sync::PoisonError::into_inner) = (pass, last);
                stats.stopped_pass.store(pass, std::sync::atomic::Ordering::Release);
            }
        })));
        self.chase_feed = Arc::downgrade(feed);''')
    rep('sync_output.rs','            if let Err(err) = port.submit(e.at, bytes, retry, stats) {','''            let result = if e.route == 0 && bytes == [0xf8] && self.routes[0].as_ref().is_some_and(|r| r.offset == 0) {
                port.submit_beat(e.at, e.transport.0, stats)
            } else {
                port.submit(e.at, bytes, retry, stats)
            };
            if let Err(err) = result {''')
    rep('midi.rs','    pub fn set_clock_follow(&self,','''    #[cfg(any(target_os = "windows", target_os = "linux", target_os = "macos"))]
    pub(crate) fn set_clock_boundary_listener(&self, listener: Option<crate::clock_follow::BoundaryListener>) {
        let mut input = self.clock_follow.lock().unwrap_or_else(PoisonError::into_inner);
        self.clock_audio_pass.store(0, Ordering::Release);
        input.boundary_listener = listener;
    }

    pub fn set_clock_follow(&self,''')
    rep('midi.rs','            *input = Default::default();\n            input.source = port;', '''            let listener = input.boundary_listener.take();
            self.clock_audio_pass.store(0, Ordering::Release);
            *input = Default::default();
            input.boundary_listener = listener;
            input.source = port;''')
    rep('callback.rs','                        clock.origin = Some(origin);','''                        clock.origin = Some(origin);
                        if let Some(feed) = &self.midi {
                            feed.clock_audio_pass.store(clock.pass, Ordering::Release);
                        }''')
    rep('clock_follow.rs','pub(crate) struct Follower {','''pub(crate) type BoundaryListener = std::sync::Arc<dyn Fn(Option<i64>) + Send + Sync>;

pub(crate) struct Follower {
    pub(crate) boundary_listener: Option<BoundaryListener>,''')
    rep('clock_follow.rs','            edge: Default::default(),','            boundary_listener: None,\n            edge: Default::default(),')
    rep('clock_follow.rs','    pub(crate) fn lost(&mut self) {','''    pub(crate) fn lost(&mut self) {
        if let Some(listener) = &self.boundary_listener {
            listener(None);
        }''')
    rep('clock_follow.rs','                0xfa => {','''                0xfa => {
                    if let Some(listener) = &self.boundary_listener {
                        listener(None);
                    }''')
    rep('clock_follow.rs','                    if self.state != State::Locked {\n                        self.awaiting_clock', '''                    if self.state != State::Locked {
                        if let Some(listener) = &self.boundary_listener {
                            listener(None);
                        }
                        self.awaiting_clock''')
    rep('clock_follow.rs','                0xfc => {','''                0xfc => {
                    if self.state == State::Locked && let Some(listener) = &self.boundary_listener {
                        listener(Some(self.played_pulse));
                    }''')
    rep('sync_output/port_io.rs','    retry: bool,\n}', '    retry: bool,\n    clock_pass: Option<u64>,\n}')
    rep('sync_output/port_io.rs','        self.staged.push(Packet { at, bytes: Bytes::new(bytes), retry });','        self.staged.push(Packet { at, bytes: Bytes::new(bytes), retry, clock_pass: None });')
    rep('sync_output/port_io.rs','    fn flush(&mut self) {','''    fn submit_beat(&mut self, at: Instant, pass: u64, _stats: &Stats) -> Result<(), String> {
        self.staged.push(Packet { at, bytes: Bytes::new(&[0xf8]), retry: false, clock_pass: Some(pass) });
        Ok(())
    }
    fn flush(&mut self) {''')
    rep('sync_output/port_io.rs','                for packets in rx {','''                let mut next_pulse: Option<i64> = None;
                let mut rolling = false;
                for packets in rx {''')
    rep('sync_output/port_io.rs','                        match connection.send_at(p.at, msg) {','''                        // Decode this destination's musical position in wire order, including
                        // a nonzero SPP before Continue. A reconnection starts with no position.
                        match msg {
                            [0xfa] => { next_pulse = Some(0); rolling = true; }
                            [0xfb] => rolling = true,
                            [0xfc] => rolling = false,
                            [0xf2, lo, hi] => next_pulse = Some(6 * (i64::from(*lo) | (i64::from(*hi) << 7))),
                            [0xf8] if rolling => {
                                if let (Some(pass), Some(pulse)) = (p.clock_pass, next_pulse)
                                    && pass != 0
                                    && stats.stopped_pass.load(std::sync::atomic::Ordering::Acquire) == pass
                                {
                                    let (stopped, last) = *stats.stopped_boundary.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
                                    if stopped == pass && pulse > last {
                                        return None;
                                    }
                                }
                                next_pulse = next_pulse.map(|n| n.saturating_add(1));
                            }
                            _ => {}
                        }
                        match connection.send_at(p.at, msg) {''')

