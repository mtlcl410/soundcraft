$env:PYTHONUTF8='1'
python ../brake-candidate/pcm-latest.py
python ../brake-candidate/phase-shim.py
python ../brake-candidate/refs.py
& 'E:/soundcraft/tools/rustup/toolchains/stable-x86_64-pc-windows-msvc/bin/rustc.exe' '@../brake-candidate/pcm.rsp'
if ($LASTEXITCODE -eq 0){& ../brake-candidate/pcm_probe.exe 'dj_tempos::' --nocapture --test-threads=3 *> ../evidence/phase-latest.log}
Select-String -Path ../evidence/phase-latest.log -Pattern 'panicked' -Context 0,1 | ForEach-Object {$_.Line; $_.Context.PostContext}
