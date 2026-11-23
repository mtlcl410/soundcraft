param([Parameter(Mandatory=$true)][string]$CargoLog)
$ErrorActionPreference = 'Stop'
$report=[IO.File]::ReadAllText((Resolve-Path -LiteralPath $CargoLog))
$evidence=Join-Path $PSScriptRoot evidence
$ui=[regex]::Match($report,'Running unittests[^\r\n]*\(([^\r\n)]+soundcraft_ui_egui-[a-f\d]+\.exe)\)').Groups[1].Value
$dsp=[regex]::Match($report,'Running unittests[^\r\n]*\(([^\r\n)]+soundcraft_playback-[a-f\d]+\.exe)\)').Groups[1].Value
if (!(Test-Path -LiteralPath $ui) -or !(Test-Path -LiteralPath $dsp)) {throw "Need finished UI and playback harnesses"}
$green=Join-Path $evidence f69-a6-feature-green.exe
Copy-Item -LiteralPath $ui -Destination $green
& (Join-Path $PSScriptRoot measure-history-ab.ps1) -Evidence $evidence -RedExe (Join-Path $evidence f69-a6-feature-red.exe) -GreenExe $green
& $ui 'app::clock_follow::' --test-threads=1 *> (Join-Path $evidence f69-follow-ui-regression.log)
$uiCode=$LASTEXITCODE
& $dsp clock_correction_arriving clock_compaction_can_publish external_clock_returns_prior_snapshot --test-threads=1 *> (Join-Path $evidence f69-follow-callback-regression.log)
$dspCode=$LASTEXITCODE
Get-Content (Join-Path $evidence f69-follow-ui-regression.log) -Tail 5
Get-Content (Join-Path $evidence f69-follow-callback-regression.log) -Tail 3
if($uiCode -or $dspCode) {exit 1}
