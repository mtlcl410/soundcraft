param([string]$tag="trial")
python ../edge-probe/make_pcm.py
cmd /c 'call E:\\soundcraft\\tools\\VSBuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat >nul && E:\\soundcraft\\tools\\rustup\\toolchains\\stable-x86_64-pc-windows-msvc\\bin\\rustc.exe @..\edge-probe\pcm.rsp' *> ../evidence/edge-pcm-build.log
if ($LASTEXITCODE) {Get-Content ../evidence/edge-pcm-build.log -First 24; exit 1}
& ../edge-probe/pcm.exe --nocapture --test-threads=2 *> ../evidence/edge-$tag.log
Get-Content ../evidence/edge-$tag.log | Select-String 'CLASS|assertion|test result'
