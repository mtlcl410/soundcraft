#![allow(dead_code)]
#[path="before_fit.rs"] mod before;
#[path="E:/soundcraft/compatibility-audit/g11-hw-acceptance/overnight-g11/crates/playback/src/sync_input.rs"] mod after;
use std::hint::black_box;
use std::time::Instant;
use std::sync::atomic::{AtomicU64,Ordering::Relaxed};
macro_rules! fit { ($m:ident,$queries:expr) => {{
    let mut f = $m::PulseFit::<192>::default();
    let t=Instant::now();
    let mut t_us=0;
    let mut yes=0;
    for tick in 0..180_000 {
        t_us += 20_000 + ((tick*97)%2300) - 1150;
        f.push(tick,t_us);
        for _ in 0..$queries { yes += black_box(&f).is_tempo_ramp() as usize; }
    }
    (t.elapsed().as_nanos() as f64 / 180_000.,yes as u64)
}}}
fn atom(guard: bool) -> (f64,u64) {
    let v = [const {AtomicU64::new(0)};3];
    let t=Instant::now();
    for i in 0..2_000_000u64 {
        let gap=black_box(5000+i%997);
        let catchup=black_box((i%1000==0) as u64);
        let dropped=black_box((i%2000==0) as u64);
        if !guard || gap>v[0].load(Relaxed) {v[0].fetch_max(gap,Relaxed);}
        if !guard || catchup!=0 {v[1].fetch_add(catchup,Relaxed);}
        if !guard || dropped!=0 {v[2].fetch_add(dropped,Relaxed);}
    }
    (t.elapsed().as_nanos() as f64/2e6,v.iter().map(|x|x.load(Relaxed)).sum())
}
include!("percentiles.rs");
fn p95(new:bool) -> (f64,u64) {
    let mut v=[0u32;32]; let mut sum=0u64; let t=Instant::now();
    for i in 0..1_000_000u32 {
        v[i as usize%32]=i.wrapping_mul(2654435761) %19000;
        let count=black_box(32);
        let val=if new {percentile95(black_box(&v),count)} else {let mut c=*black_box(&v);c[..count].sort_unstable();c[(count*95).div_ceil(100)-1]};
        sum+=u64::from(val);
    }
    (t.elapsed().as_nanos() as f64/1e6,sum)
}
fn main() {
    for rep in 0..9 {
        for new in [rep%2==0,rep%2!=0] {
            for q in [1,4,16] {
                let (ns,c)=if new {fit!(after,q)} else {fit!(before,q)};
                println!("fit{q},{rep},{new},{ns:.3},{c}");
            }
            for (name,(ns,c)) in [("atom",atom(new)),("p95",p95(new))] {println!("{name},{rep},{new},{ns:.3},{c}");}
        }
    }
}
