param(
 [Parameter(Mandatory=$true)][string]$RedExe,
 [Parameter(Mandatory=$true)][string]$GreenExe,
 [Parameter(Mandatory=$true)][string]$Evidence
)
$ErrorActionPreference = 'Stop'
$rows = [System.Collections.Generic.List[object]]::new()
foreach ($round in 1..5) {
    $versions = if ($round % 2) { @('old','new') } else { @('new','old') }
    foreach ($version in $versions) {
        $exe = if ($version -eq 'old') { $RedExe } else { $GreenExe }
        $prefix = Join-Path $Evidence "f69-a6-$round-$version"
        "Running unittests ($exe)" | Set-Content "$prefix-cmd.log" -Encoding UTF8
        & (Join-Path $PSScriptRoot history-rss.ps1) -CargoLog "$prefix-cmd.log" -Destination "$prefix.log"
        $s = Get-Content "$prefix.log" -Raw
        $m = [regex]::Match($s,'pulses=(\d+) changes=(\d+) edits=(\d+) peak_events=(\d+) final_events=(\d+) end_publish_p95_us=([\d.]+)')
        $rss = [regex]::Match($s,'working set bytes=(\d+) .*ExitCode=(\d+)')
        if (!$m.Success -or !$rss.Success) {throw "missing instrumentation in $prefix.log"}
        $rows.Add([pscustomobject]@{Version=$version;Round=$round;Pulses=$m.Groups[1].Value;Changes=$m.Groups[2].Value;Edits=$m.Groups[3].Value;PeakEvents=$m.Groups[4].Value;EndEvents=$m.Groups[5].Value;PublishP95us=[double]$m.Groups[6].Value;PeakRssBytes=[long]$rss.Groups[1].Value;ExitCode=$rss.Groups[2].Value})
    }
}
$rows | ConvertTo-Json | Set-Content (Join-Path $Evidence 'f69-history-ab.json')
$rows | Format-Table
