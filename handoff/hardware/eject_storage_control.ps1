param(
    [Parameter(Mandatory)][string] $RunFolder,
    [Parameter(Mandatory)][ValidateRange(1,3)][int] $Cycle
)
$ErrorActionPreference = 'Stop'
$run = (Resolve-Path -LiteralPath $RunFolder).Path
if (!(Test-Path -LiteralPath (Join-Path $run "ready-$Cycle.json"))) {
    throw 'No ready signal for this cycle.'
}
$receipt = Join-Path $run "safe-eject-$Cycle.json"
if (Test-Path -LiteralPath $receipt) { throw 'This cycle already has an eject receipt.' }
$deadline = (Get-Date).AddMinutes(30)
do {
    $cards = @([IO.DriveInfo]::GetDrives() | Where-Object {
        $_.DriveType -eq 'Removable' -and $_.IsReady -and
        (Test-Path -LiteralPath (Join-Path $_.RootDirectory.FullName 'MTR/040209_0002/song.sys'))
    })
    if ($cards.Count -gt 1) { throw 'More than one card matches; nothing ejected.' }
    if ($cards.Count -eq 1) { break }
    if ((Get-Date) -gt $deadline) { throw 'Model 12 SD not seen.' }
    Start-Sleep -Milliseconds 500
} while ($true)
$card = $cards[0]
$drive = $card.Name.Substring(0,2)
$mounted = Get-Date -Format o
Start-Sleep -Seconds 3
if (!(Test-Path -LiteralPath (Join-Path $card.RootDirectory.FullName 'MTR/040209_0002/song.sys'))) {
    throw 'Card no longer matches.'
}
$item = (New-Object -ComObject Shell.Application).Namespace(17).ParseName($drive)
if (!$item) { throw 'Card is missing in Explorer.' }
$item.InvokeVerb('Eject')
for ($i = 0; $i -lt 80; $i++) {
    Start-Sleep -Milliseconds 250
    if (!([IO.DriveInfo]::new($drive).IsReady)) {
        @{ letter=$drive; cycle=$Cycle; mounted=$mounted; safely_ejected=(Get-Date -Format o) } |
            ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8
        Get-Content -LiteralPath $receipt
        exit 0
    }
}
throw 'Windows has not confirmed ejection. Remain in STORAGE.'
