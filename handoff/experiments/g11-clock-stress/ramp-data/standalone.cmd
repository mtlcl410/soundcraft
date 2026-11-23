@echo off
setlocal
set "CARGO_HOME=E:\soundcraft\tools\cargo"
set "RUSTUP_HOME=E:\soundcraft\tools\rustup"
set "PATH=%CARGO_HOME%\bin;%PATH%"
call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul
cd /d E:\soundcraft\compatibility-audit\g11-clock-stress\ramp-data
rustc --edition=2024 --test pulse-standalone-red.rs -o pulse-standalone-red.exe
if errorlevel 1 exit /b 1
pulse-standalone-red.exe --nocapture
rustc --edition=2024 --test pulse-standalone-green.rs -o pulse-standalone-green.exe
if errorlevel 1 exit /b 1
pulse-standalone-green.exe --nocapture
