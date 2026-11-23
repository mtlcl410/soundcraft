param(
 [Parameter(Mandatory=$true)][string]$TestExe,
 [Parameter(Mandatory=$true)][string]$Evidence,
 [ValidateRange(1,20)][int]$Rounds=3
)
$ErrorActionPreference = 'Stop'
[void][IO.Directory]::CreateDirectory($Evidence)
$Evidence = (Resolve-Path -LiteralPath $Evidence).Path
$TestExe = (Resolve-Path -LiteralPath $TestExe).Path
[pscustomobject]@{TestExe=$TestExe;SHA256=(Get-FileHash -LiteralPath $TestExe -Algorithm SHA256).Hash;DateTime=(Get-Date).ToString('o');Rounds=$Rounds} | ConvertTo-Json | Set-Content (Join-Path $Evidence 'a6-run.json') -Encoding utf8
$rows = [System.Collections.Generic.List[object]]::new()
foreach ($round in 1..$Rounds) {
    $versions = if ($round % 2) { @('uncapped','capped') } else { @('capped','uncapped') }
    foreach ($version in $versions) {
        $name = if ($version -eq 'uncapped') { 'six_hour_clock_history_uncapped_control' } else { 'six_hour_clock_history_has_bounded_unreferenced_events' }
        $prefix = Join-Path $Evidence "a6-same-build-$round-$version"
        "Running unittests ($TestExe)" | Set-Content "$prefix-cmd.log" -Encoding UTF8
        & (Join-Path $PSScriptRoot history-rss.ps1) -CargoLog "$prefix-cmd.log" -Destination "$prefix.log" -TestName $name
        $s = Get-Content "$prefix.log" -Raw
        $m = [regex]::Match($s,'pulses=(\d+) changes=(\d+) edits=(\d+) peak_events=(\d+) final_events=(\d+) end_publish_p95_us=([\d.]+)')
        $rss = [regex]::Match($s,'working set bytes=(\d+) .*ExitCode=(\d+)')
        if (!$m.Success -or !$rss.Success -or $rss.Groups[2].Value -ne "0") {throw "missing instrumentation in $prefix.log"}
        $rows.Add([pscustomobject]@{Version=$version;Round=$round;Pulses=$m.Groups[1].Value;Changes=$m.Groups[2].Value;Edits=$m.Groups[3].Value;PeakEvents=$m.Groups[4].Value;EndEvents=$m.Groups[5].Value;PublishP95us=[double]$m.Groups[6].Value;PeakRssBytes=[long]$rss.Groups[1].Value;ExitCode=$rss.Groups[2].Value})
    }
}
$rows | ConvertTo-Json | Set-Content (Join-Path $Evidence 'a6-same-build-results.json')
$rows | Format-Table
