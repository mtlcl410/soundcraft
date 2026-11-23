from pathlib import Path
import subprocess
d=Path(__file__).resolve().parent
kind='crates/mix/src/midi_clip_bounds.rs'
tests=Path('stale_bounds_ci.rs').read_text(encoding='utf8').replace('\n\n}\n','\n}\n')
s=(d/'red69dj'/kind).read_text(encoding='utf8')
fixed=s.replace('struct ClipBounds {','struct ClipBounds {\n    id: ClipId,').replace('bounds.push(ClipBounds {','bounds.push(ClipBounds {\n                            id: c.id,').replace('    /// Apply to the same playlist layout used by `from_score`, before changing its structure.', '    /// Apply only to clips still present at the cached location.').replace('            let clip = &mut session.tracks[b.track].playlists[b.playlist].clips[b.clip];','''            let Some(clip) = session.tracks.get_mut(b.track)
                .and_then(|track| track.playlists.get_mut(b.playlist))
                .and_then(|playlist| playlist.clips.get_mut(b.clip))
                .filter(|clip| clip.id == b.id) else { continue };''')
alltests=(d/'red69dj/crates/mix/src/tests.rs').read_text(encoding='utf8')
fixture=alltests[alltests.index('fn synth_session('):].split('\n}\n',1)[0]+'\n}\n'
fixture=fixture.replace('ins.params.insert(', 'ins.params.insert(')
for tag,src in [('red',s),('green',fixed)]:
 (d/'evidence/bounds.rs').write_text('mod bounds {\n'+src+'}\nuse bounds::MidiClipBeatBounds;use soundcraft_model::{Session,Insert,TrackKind,Clip};use soundcraft_model::ChannelFormat;\n'+fixture+tests,encoding='utf8')
 argv=(d/'brake-candidate/pcm.rsp').read_text(encoding='utf8').splitlines()
 argv[2]=str(d/'evidence/bounds.rs')
 argv[argv.index('-o')+1]=str(d/'evidence/bounds.exe')
 (d/'evidence/bounds.rsp').write_text('\n'.join(argv))
 subprocess.run('call E:\\soundcraft\\tools\\VSBuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat >nul && E:\\soundcraft\\tools\\rustup\\toolchains\\stable-x86_64-pc-windows-msvc\\bin\\rustc.exe @evidence/bounds.rsp',shell=True,check=True)
 res=subprocess.run([d/'evidence/bounds.exe'],capture_output=True)
 (d/f'evidence/F69-2-{tag}-isolated.log').write_bytes(res.stdout+res.stderr)
 assert (res.returncode==0)==(tag=='green')
(d/'follow'/kind).write_text(fixed,encoding='utf8')
p=d/'follow/crates/mix/src/tests.rs'
p.write_text(p.read_text(encoding='utf8')+'\n'+tests,encoding='utf8')


