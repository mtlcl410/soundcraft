@echo off
setlocal
call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul || exit /b 1
set "sdk=%TEMP%\soundcraft-review-sdk\ASIOSDK"
if not exist "%~dp0build\storage-sdk" mkdir "%~dp0build\storage-sdk"
pushd "%~dp0build\storage-sdk" || exit /b 1
set "player=storage-sdk.exe"
if "%~1"=="reopen" set "player=storage-sdk-reopen.exe"
cl /nologo /O2 /EHsc /std:c++17 /I"%sdk%\common" /I"%sdk%\host" /I"%sdk%\host\pc" "%~dp0storage_sdk_player.cpp" "%sdk%\common\asio.cpp" "%sdk%\host\asiodrivers.cpp" "%sdk%\host\pc\asiolist.cpp" /Fe%player% /link ole32.lib advapi32.lib user32.lib
exit /b %errorlevel%
