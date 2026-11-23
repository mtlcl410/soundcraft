@echo off
call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul
E:\soundcraft\tools\rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\rustc.exe --edition 2024 -C opt-level=3 bench.rs -o bench.exe
if errorlevel 1 exit /b 1
bench.exe > bench.csv
