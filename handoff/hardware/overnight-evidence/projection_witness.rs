// Compile only the production conversion, with the public data it reads.
use std::{time::{Duration, Instant}, env, fs};
#[derive(Clone,Copy,Default)]
struct Snapshot { bpm:Option<f64>, phase_grid_bpm:Option<f64>, brake_grid_bpm:Option<f64>, stamp_us:i64, now_us:i64 }
#[derive(Clone,Copy)] struct SampleRate;
impl SampleRate { fn as_f64(self)->f64{48_000.} }
#[path="../morning-device-grid/crates/ui-egui/src/app/clock_follow/device_time.rs"] mod device_time;
fn main() {
    let text=fs::read_to_string(env::args().nth(1).unwrap()).unwrap();
    let base=Instant::now()+Duration::from_secs(1); let mut cal=device_time::DeviceTime::default();
    let mut error=Vec::new(); let mut raw=Vec::new();
    for row in text.lines() {
        let v:Vec<_>=row.split_whitespace().map(|w|w.parse::<f64>().unwrap()).collect();
        let wall=(v[0]*1e6) as i64;
        let observed=if v[1]>=0. { base+Duration::from_nanos(v[1] as u64) } else { base-Duration::from_nanos((-v[1]) as u64) };
        let snapshot=Snapshot{now_us:wall,stamp_us:wall+500_000,bpm:Some(120.),..Default::default()};
        let adj=cal.project(snapshot,Some((0,0)),SampleRate,||Some((1,observed,v[2])));
        raw.push(((snapshot.stamp_us as f64*0.048-v[3])/48.).abs());
        error.push(((adj.stamp_us as f64*0.048-v[3])/48.).abs());
    }
    for (label,mut v) in [("nominal",raw),("device",error)] {
        let end=*v.last().unwrap(); v.sort_by(f64::total_cmp);
        println!("{label} {} forecasts, ms p50 {:.4} p99 {:.4} max {:.4} end {:.4}",v.len(),v[v.len()/2],v[v.len()*99/100],v[v.len()-1],end);
        if label=="device" {assert!(v[v.len()-1]<4.);}
    }
}
