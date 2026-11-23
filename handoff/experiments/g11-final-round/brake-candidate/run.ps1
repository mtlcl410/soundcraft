$ErrorActionPreference='Stop'
python ../brake-candidate/pcm_probe.py
python ../brake-candidate/refs.py
& 'E:/soundcraft/tools/rustup/toolchains/stable-x86_64-pc-windows-msvc/bin/rustc.exe' '@../brake-candidate/pcm.rsp'
if ($LASTEXITCODE -eq 0) {& ../brake-candidate/pcm_probe.exe brake --nocapture --test-threads=3 *> ../evidence/dj-brake-candidate.log}
Get-Content ../evidence/dj-brake-candidate.log -Tail 5
