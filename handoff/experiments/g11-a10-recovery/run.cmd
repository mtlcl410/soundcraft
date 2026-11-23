@echo off
setlocal
set "CARGO_HOME=E:\soundcraft\tools\cargo"
set "RUSTUP_HOME=E:\soundcraft\tools\rustup"
set "CARGO_NET_OFFLINE=true"
set "CARGO_BUILD_JOBS=4"
set "PATH=%CARGO_HOME%\bin;%PATH%"
call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul
cargo %*
exit /b %errorlevel%
