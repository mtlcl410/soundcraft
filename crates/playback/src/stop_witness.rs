// Private acceptance build, one selected output. Process-local monotonic nanoseconds.
use std::sync::atomic::{AtomicI64, Ordering::Relaxed};
use std::sync::OnceLock;
use std::time::Instant;

pub(super) static IN_FC: AtomicI64 = AtomicI64::new(0);
pub(super) static HOST_STOP: AtomicI64 = AtomicI64::new(0);
pub(super) static AUDIO_STOP: AtomicI64 = AtomicI64::new(0);
static F8_BEGIN: AtomicI64 = AtomicI64::new(0);
static F8_END: AtomicI64 = AtomicI64::new(0);

pub(super) fn qpc() -> i64 {
    static EPOCH: OnceLock<Instant> = OnceLock::new();
    EPOCH.get_or_init(Instant::now).elapsed().as_nanos() as i64 + 1
}
pub(super) fn mark(stage: &AtomicI64) {
    stage.store(qpc(), Relaxed);
}
pub(super) fn after_send(status: u8, begin: i64) {
    let end = qpc();
    if status == 0xf8 {
        F8_BEGIN.store(begin, Relaxed);
        F8_END.store(end, Relaxed);
    } else {
        eprintln!("SC_STOP_QPC {} {} {} {} {} {} {}", IN_FC.load(Relaxed), HOST_STOP.load(Relaxed),
                  AUDIO_STOP.load(Relaxed), F8_BEGIN.load(Relaxed), F8_END.load(Relaxed), begin, end);
    }
}
