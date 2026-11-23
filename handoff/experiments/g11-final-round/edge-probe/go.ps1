param([string]$tag="trial")
python ../edge-probe/run.py
cmd /c 'call E:\\soundcraft\\tools\\VSBuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat >nul && E:\\soundcraft\\tools\\rustup\\toolchains\\stable-x86_64-pc-windows-msvc\\bin\\rustc.exe --test --edition=2024 -C opt-level=2 ../edge-probe/probe.rs -o ../edge-probe/probe.exe' *> ../evidence/edge-build.log
if ($LASTEXITCODE) {Get-Content ../evidence/edge-build.log -First 24; exit 1}
& ../edge-probe/probe.exe --nocapture *> ../evidence/edge-$tag.log
Get-Content ../evidence/edge-$tag.log | Select-String 'CLASS|assertion|test result'
