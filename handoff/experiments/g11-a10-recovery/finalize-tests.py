from pathlib import Path
d=Path(__file__).resolve().parent
for n in ['beat','mtc','follow']:
 p=d/n/'crates/playback/src'
 for file,old,replace in [('sync_output_tests.rs','a10_first_clock','clock.rs'),('mtc_sync_output_tests.rs','scenario_a10_dual','qf.rs')]:
  f=p/file
  if not f.exists():continue
  text=f.read_text().split('\n#[test]\nfn '+old)[0].rstrip()
  new=(d/replace).read_text(encoding='utf-8-sig').replace('let locate_frame = (recovery_ms / 40) as i64;', 'let locate_frame = (recovery_ms / 40) as u8;').replace('crate::mtc::locate(locate_frame, song.frame_rate).to_vec()', 'vec![0xf0, 0x7f, 0x7f, 1, 1, 0x20, 0, 0, locate_frame, 0xf7]')
  f.write_bytes((text+'\n\n'+new.strip()+'\n').encode())
