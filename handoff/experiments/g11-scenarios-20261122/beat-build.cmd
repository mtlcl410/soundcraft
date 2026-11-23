@echo off
setlocal
set "CARGO_HOME=E:\soundcraft\tools\cargo"
set "RUSTUP_HOME=E:\soundcraft\tools\rustup"
set "CARGO_NET_OFFLINE=true"
set "CARGO_TARGET_DIR=E:\soundcraft\compatibility-audit\g11-verify-beat-target"
set "CARGO_BUILD_JOBS=3"
set "PATH=%CARGO_HOME%\bin;%PATH%"
call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul
cargo %*
exit /b %errorlevel%
