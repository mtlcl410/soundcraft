param([string]$tag="candidate")
cmd /c 'call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul && E:\soundcraft\tools\rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\rustc.exe @..\packed-old-probe\mix.rsp' *> ../evidence/packed-old-mix-build.log
if ($LASTEXITCODE) {Get-Content ../evidence/packed-old-mix-build.log -First 22;exit 1}
python -X utf8 ../packed-old-probe/build.py
cmd /c 'call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul && E:\soundcraft\tools\rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\rustc.exe @..\packed-old-probe\pcm.rsp' *> ../evidence/packed-old-build.log
if ($LASTEXITCODE) {Get-Content ../evidence/packed-old-build.log -First 22;exit 1}
$env:SOUNDCRAFT_PACKET_TRACE='1'
& ../packed-old-probe/pcm.exe trailing_packed_slowdowns --nocapture --test-threads=1 *> ../evidence/$tag.log
python -X utf8 ../evidence/packed_summary.py $tag > ../evidence/$tag-summary.txt
Get-Content ../evidence/$tag-summary.csv
