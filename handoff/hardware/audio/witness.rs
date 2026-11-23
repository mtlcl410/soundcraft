//! Local hardware measurement only. The two channels come from the same ASIO buffer switch.
use super::{asio_channel_info, AsioBufferInfo, Driver};
use std::{env, fs::{File,OpenOptions}, io::{BufWriter,Write}, path::PathBuf,
    sync::{Mutex, atomic::{AtomicUsize,Ordering}, mpsc::{self,SyncSender}}};

unsafe extern "system" {
    fn QueryPerformanceCounter(n: *mut i64) -> i32;
    fn QueryPerformanceFrequency(n: *mut i64) -> i32;
}
fn qpc() -> u64 {let mut n=0;unsafe{QueryPerformanceCounter(&mut n)};n as u64}
#[derive(Clone,Copy)]
struct Side { ptr:[usize;2], format:i32 }
struct Capture { tx:SyncSender<Block>, input:Side, output:Side, n:usize, serial:u64 }
struct Block { pos:u64, system:u64, qpc:u64, serial:u64, flags:i32, n:u32, samples:[f32;1024] }
static ACTIVE:Mutex<Option<Capture>>=Mutex::new(None);
static EPOCH:AtomicUsize=AtomicUsize::new(0);

pub(super) fn setup(driver:&Driver,buffers:&[AsioBufferInfo],n:i32) {
    let Some(path)=env::var_os("SC_ASIO_EVIDENCE") else{return};
    let path=PathBuf::from(path);
    let mut active=ACTIVE.lock().unwrap();
    *active=None;
    if !(1..=512).contains(&n){return}
    let return_channel:i32=env::var("SC_ASIO_RETURN_INDEX").expect("one zero-based return").parse().unwrap();
    let side=|input:bool,channel:i32|->Option<Side>{
        let b=buffers.iter().find(|b| (b.is_input!=0)==input && b.channel_num==channel)?;
        let ptr=b.buffers;
        let info=asio_channel_info(channel,input).ok()?;
        let format=info.type_ as i32;
        Some(Side{ptr:[ptr[0] as usize,ptr[1] as usize],format})
    };
    let (Some(input),Some(output))=(side(true,return_channel),side(false,0)) else{return};
    let lat=driver.latencies().expect("ASIOGetLatencies");
    let sr=driver.sample_rate().expect("ASIOGetSampleRate");
    let mut freq=0;
    unsafe{QueryPerformanceFrequency(&mut freq)};
    let epoch=EPOCH.fetch_add(1,Ordering::SeqCst);
    let fields=format!(r#"{{"sample_rate":{sr},"buffer":{n},"input_index":{return_channel},"output_index":0,"input_latency":{},"output_latency":{},"input_format":{},"output_format":{},"qpc_frequency":{freq}}}"#,lat.input,lat.output,input.format,output.format);
    assert!([16,17,18,19,20,24,25,26,27].contains(&input.format)&&[16,17,18,19,20,24,25,26,27].contains(&output.format),"unsupported ASIO sample format");
    let file=OpenOptions::new().write(true).create_new(true).open(path.join(format!("epoch-{epoch}.bin"))).unwrap();
    File::create_new(path.join(format!("epoch-{epoch}.json"))).unwrap().write_all(fields.as_bytes()).unwrap();
    let (tx,rx)=mpsc::sync_channel::<Block>(512);
    std::thread::spawn(move||{
        let mut w=BufWriter::with_capacity(256*1024,file);
        for b in rx {
            for v in [b.pos,b.system,b.qpc,b.serial]{w.write_all(&v.to_le_bytes()).unwrap()}
            w.write_all(&b.flags.to_le_bytes()).unwrap();
            w.write_all(&b.n.to_le_bytes()).unwrap();
            let data=&b.samples[..2*b.n as usize];
            let bytes=unsafe{std::slice::from_raw_parts(data.as_ptr().cast::<u8>(),std::mem::size_of_val(data))};
            w.write_all(bytes).unwrap();
        }
        w.flush().unwrap();
    });
    *active=Some(Capture{input,output,n:n as usize,tx,serial:0});
}
fn value(side:Side,k:usize,index:usize)->f32 {
    let p=side.ptr[index] as *const u8;
    unsafe{match side.format {
        16=>p.cast::<i16>().add(k).read_unaligned() as f32/32768.,
        17=>{let a=p.add(3*k);i32::from_le_bytes([0,*a,*a.add(1),*a.add(2)]) as f32/2147483648.},
        18=>p.cast::<i32>().add(k).read_unaligned() as f32/2147483648.,
        19=>p.cast::<f32>().add(k).read_unaligned(),
        20=>p.cast::<f64>().add(k).read_unaligned() as f32,
        24..=27=>{let bits=[16,18,20,24][(side.format-24) as usize];p.cast::<i32>().add(k).read_unaligned() as f32/(1u32<<(bits-1)) as f32},
        _=>unreachable!(),
    }}
}
pub(super) fn clear(){if let Ok(mut c)=ACTIVE.lock(){c.take();}}
pub(super) fn capture(index:usize,pos:u64,system:u64,flags:i32){
    if let Ok(mut lock)=ACTIVE.try_lock(){
        if let Some(c)=lock.as_mut(){
            c.serial+=1;
            let mut b=Block{pos,system,qpc:qpc(),serial:c.serial,flags,n:c.n as u32,samples:[0.;1024]};
            for (k,pair) in b.samples[..2*c.n].chunks_exact_mut(2).enumerate(){
                pair[0]=value(c.output,k,index);pair[1]=value(c.input,k,index);
            }
            let _=c.tx.try_send(b);
        }
    }
}
