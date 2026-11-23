// Private acceptance build, one selected output. Values are Windows QPC ticks.
use std::sync::atomic::{AtomicI64, Ordering::Relaxed};

#[link(name = "kernel32")]
unsafe extern "system" {
    fn QueryPerformanceCounter(result: *mut i64) -> i32;
}

pub(super) static IN_FC: AtomicI64 = AtomicI64::new(0);
pub(super) static HOST_STOP: AtomicI64 = AtomicI64::new(0);
pub(super) static AUDIO_STOP: AtomicI64 = AtomicI64::new(0);
static F8_BEGIN: AtomicI64 = AtomicI64::new(0);
static F8_END: AtomicI64 = AtomicI64::new(0);

pub(super) fn qpc() -> i64 {
    let mut value = 0;
    unsafe { QueryPerformanceCounter(&mut value) };
    value
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
