python ../brake-candidate/pcm_probe.py
python ../brake-candidate/phase-narrow.py
python ../brake-candidate/refs.py
& 'E:/soundcraft/tools/rustup/toolchains/stable-x86_64-pc-windows-msvc/bin/rustc.exe' '@../brake-candidate/pcm.rsp'
if ($LASTEXITCODE -eq 0) {& ../brake-candidate/pcm_probe.exe 'dj_tempos::' --nocapture --test-threads=3 *> ../evidence/phase-v1.log}
Select-String -Path ../evidence/phase-v1.log -Pattern 'panicked' -Context 0,1 | ForEach-Object {$_.Line; $_.Context.PostContext}
