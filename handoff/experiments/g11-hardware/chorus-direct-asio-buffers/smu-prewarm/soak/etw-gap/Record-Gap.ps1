# Only WPR runs as administrator. Test playback stays in the normal desktop session.
$ErrorActionPreference = 'Stop'
$wpr = Join-Path $env:SystemRoot 'System32/wpr.exe'
$profile = (Join-Path $PSScriptRoot 'SoundCraftGap.wprp') + '!SoundCraftGap'
$instance = 'SoundCraftASIOGap'
function Wait-Signal($name, $seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($seconds)
    while (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $name))) {
        if ([DateTime]::UtcNow -gt $deadline) { throw "Timed out waiting for $name" }
        Start-Sleep -Milliseconds 350
    }
}
try {
    foreach ($size in @(64,128)) {
        Wait-Signal "start-$size.signal" 900
        $file = Join-Path $PSScriptRoot "trace-$size.etl"
        if (Test-Path -LiteralPath $file) { throw "Existing ETL: $file" }
        & $wpr -start $profile -filemode -instancename $instance 2>&1 | Out-File (Join-Path $PSScriptRoot "start-$size.log")
        if ($LASTEXITCODE -ne 0) { throw "WPR start error $LASTEXITCODE" }
        try {
            [IO.File]::WriteAllText((Join-Path $PSScriptRoot "ready-$size.signal"), [DateTime]::UtcNow.ToString('o'))
            Wait-Signal "stop-$size.signal" 360
        } finally {
            & $wpr -status collectors -details -instancename $instance 2>&1 | Out-File (Join-Path $PSScriptRoot "status-$size.log")
            & $wpr -stop $file -instancename $instance 2>&1 | Out-File (Join-Path $PSScriptRoot "stop-$size.log")
            if ($LASTEXITCODE -ne 0) { throw "WPR stop error $LASTEXITCODE" }
        }
    }
} catch {
    $_ | Out-String | Out-File (Join-Path $PSScriptRoot 'recorder-error.log')
    exit 1
}

