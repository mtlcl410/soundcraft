@echo off
call E:\soundcraft\tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat >nul
cl /nologo /EHsc /std:c++17 phase-audio.cpp ole32.lib uuid.lib /Fe:phase-audio.exe
if errorlevel 1 exit /b 1
cl /nologo /EHsc /std:c++17 tap.cpp winmm.lib /Fe:tap.exe
