from pathlib import Path
import os,sys,subprocess
a=Path(__file__).resolve().parent; d=a.parent; w=d/'overnight-g11'; src=w/'crates/playback/src'; r=d/'runs/home-20261123-002520-recorder'
p=src/'mtc/tests.rs'; saved=p.read_bytes()
probe=saved+b'\nmod overnight_replay { include!(r"'+str(a/'real_preroll_replay.rs').encode()+b'"); }\n'
probe+=b'\n#[test] fn overnight_enumerate_ports(){let m=midir::MidiOutput::new("G11 inventory").unwrap(); for p in m.ports(){println!("MIDI-OUT {:?} id={:?}",m.port_name(&p),p.id());}}\n'
def run(fil,env,log):
    with (a/log).open('wb') as f:
        subprocess.run([os.environ['COMSPEC'],'/d','/c',str(d.parent/'g11-a10-recovery/run.cmd'),'test','--offline','-p','soundcraft-playback','--lib',fil,'--','--nocapture'],env=os.environ|dict(CARGO_TARGET_DIR=str(d/'target-follow-confirm'))|env,cwd=w,stdout=f,stderr=subprocess.STDOUT,check=True)
try:
    p.write_bytes(probe)
    run('overnight_enumerate_ports',{},'midir-ports.log')
    run('overnight_replay',{'SC_FULL_TAKE_DATA':str(r/'paired-inputs.txt')},'recorded-wire-product.log')
    run('overnight_replay',{'SC_FULL_TAKE_DATA':str(a/'fresh-inputs.txt')},'fresh-wire-product.log')
finally:
    assert p.read_bytes()==probe
    p.write_bytes(saved)

