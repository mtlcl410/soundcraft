from pathlib import Path
import difflib,shutil
d=Path(__file__).resolve().parent;t=d.parents[2]/'g11-direct-asio-follow'
files={'crates/dsp/src/lib.rs':'dsp-lib.rs.orig','crates/vst3-host/src/plugin.rs':'vst3-host-plugin.rs.orig','crates/vst3-host/src/ffi/instance.rs':'instance.rs.orig','crates/playback/src/callback.rs':'playback-callback.rs.orig','crates/playback/src/stream.rs':'playback-stream.rs.orig'}
patch=[]
for rel,backup in files.items():
 p=t/rel;prior=(d/backup).read_text(encoding='utf-8');now=p.read_text(encoding='utf-8');assert prior!=now,rel
 patch.extend(difflib.unified_diff(prior.splitlines(True),now.splitlines(True),'a/'+rel,'b/'+rel))
(d/'timing-probes.patch').write_bytes(''.join(patch).encode())
for rel,backup in files.items():shutil.copyfile(d/backup,t/rel)

