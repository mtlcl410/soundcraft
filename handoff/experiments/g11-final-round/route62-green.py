from pathlib import Path
base=Path(__file__).resolve().parent
w=base/'route62'/'crates'
def edit(path,old,new):
 p=w/path;s=p.read_text(encoding='utf8');assert s.count(old)==1,old;p.write_text(s.replace(old,new),encoding='utf8')
edit('playback/src/sync_output.rs','''    pub(crate) fn timing_issue(&self) -> Option<crate::OutputTimingIssue> {
        match self.metrics.lead() {''','''    pub(crate) fn timing_issue(&self) -> Option<crate::OutputTimingIssue> {
        let clock = self.compensated && !self.beat.is_empty();
        let encoder = self.additional.as_ref().is_some_and(|(_, _, compensated)| *compensated);
        if !clock && !encoder {
            return None;
        }
        match self.metrics.lead() {''')
edit('playback/src/lib.rs','The latest unusable hardware timestamp, if the current stream reported one.','An unusable output timestamp affecting a configured, latency-compensated MIDI destination.')
edit('ui-egui/src/app/audio.rs','''        OutputTimingIssue::Unknown => {
            Some(crate::localization::text("Audio output timing is unavailable. Compensated MIDI outputs need a valid measurement.").into())
        }''','''        OutputTimingIssue::Unknown => Some(format!(
            "{} {}",
            crate::localization::text("Audio output timing is unavailable. Compensated MIDI outputs need a valid measurement."),
            crate::localization::text("Check the audio device, then use Reconnect audio device in Setup › Playback Engine.")
        )),''')
f='playback/src/stream_recovery.rs'
edit(f,'use std::sync::{Arc, Mutex};','use std::sync::{Arc, Mutex, MutexGuard, TryLockError};')
edit(f,'const MAX_ATTEMPTS: u8 = 3;','const MAX_ATTEMPTS: u8 = 3;\nconst PRESENCE_INTERVAL: Duration = Duration::from_secs(30);')
edit(f,'    healthy_since: Option<Instant>,','    healthy_since: Option<Instant>,\n    last_lookup: Option<Instant>,')
edit(f,'''    fn lookup<T>(&mut self, _now: Instant, find: impl FnOnce() -> Option<T>) -> Option<T> {
        let device = find();
        if self.can_open(device.is_some()) { device } else { None }
    }

    fn can_open(&mut self, present: bool) -> bool {
        if !present {
            self.attempts = 0;
            return false;
        }
        if self.attempts == MAX_ATTEMPTS {
            return false;
        }
        self.attempts += 1;
        true
    }''','''    fn lookup<T>(&mut self, now: Instant, find: impl FnOnce() -> Option<T>) -> Option<T> {
        let exhausted = self.attempts >= MAX_ATTEMPTS;
        if exhausted && self.last_lookup.is_some_and(|last| now.saturating_duration_since(last) < PRESENCE_INTERVAL) {
            return None;
        }
        self.last_lookup = Some(now);
        let Some(device) = find() else {
            self.attempts = 0;
            return None;
        };
        if exhausted {
            return None;
        }
        self.attempts += 1;
        Some(device)
    }''')
edit(f,'let Ok(_guard) = graph.try_lock() else {','let Some(_guard) = try_graph(graph) else {')
edit(f,'let Ok(mut graph) = graph.try_lock() else { return false };','let Some(mut graph) = try_graph(graph) else { return false };')
edit(f,'struct SharedGraph {','''// Audio and control threads must never wait for each other. Poisoning signals a previous
// unwind, not contention; an available graph still permits rendering or a stopped handoff.
fn try_graph<T>(graph: &Mutex<T>) -> Option<MutexGuard<'_, T>> {
    match graph.try_lock() {
        Ok(guard) => Some(guard),
        Err(TryLockError::Poisoned(error)) => Some(error.into_inner()),
        Err(TryLockError::WouldBlock) => None,
    }
}

struct SharedGraph {''')
edit(f,'Decision::Probe => self.probe(shared),','Decision::Probe => self.probe(now, shared),')
edit(f,'fn probe(&mut self, shared: &Arc<Shared>) {','fn probe(&mut self, now: Instant, shared: &Arc<Shared>) {')
edit(f,'self.retry.lookup(Instant::now(), ||','self.retry.lookup(now, ||')
edit(f,'assert!(!retry.can_open(false));','assert!(retry.lookup(now, || None::<()>).is_none());') if False else None
p=w/f;s=p.read_text(encoding='utf8');s=s.replace('assert!(!retry.can_open(false));','assert!(retry.lookup(now, || None::<()>).is_none());',1).replace('assert!(retry.can_open(true));\n            retry.decide','assert!(retry.lookup(now, || Some(())).is_some());\n            retry.decide').replace('''        assert!(!retry.can_open(true));
        assert!(!retry.can_open(false));
        assert!(retry.can_open(true));''','''        assert!(retry.lookup(now, || Some(())).is_none());
        let later = now + PRESENCE_INTERVAL;
        assert!(retry.lookup(later, || None::<()>).is_none());
        assert!(retry.lookup(later, || Some(())).is_some());''');assert 'can_open(' not in s;p.write_text(s,encoding='utf8')
