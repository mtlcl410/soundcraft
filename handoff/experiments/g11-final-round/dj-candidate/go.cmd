@echo off
cd /d E:\soundcraft\compatibility-audit\g11-final-round\brake69
python ..\dj-candidate\make.py
if errorlevel 1 exit /b 1
call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul
E:\soundcraft\tools\rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\rustc.exe @..\dj-candidate\try.rsp
if errorlevel 1 exit /b 1
..\dj-candidate\try.exe dj_tempos:: --nocapture --test-threads=2 > ..\evidence\dj-%1.log 2>&1
exit /b %errorlevel%
