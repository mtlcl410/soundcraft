$ErrorActionPreference = 'Stop'
$cards = @(Get-PSDrive -PSProvider FileSystem | Where-Object {
    $_.Name.Length -eq 1 -and
    (Test-Path -LiteralPath (Join-Path $_.Root 'MTR/040208_0011')) -and
    (Test-Path -LiteralPath (Join-Path $_.Root 'MTR/040208_0020'))
})
if ($cards.Count -ne 1) { throw 'The Model 12 test card could not be uniquely identified.' }
$letter = $cards[0].Name
$drive = [System.IO.DriveInfo]::new($letter)
if ($drive.DriveType -ne 'Removable') { throw "Unexpected drive type for ${letter}: $($drive.DriveType)" }
$shell = New-Object -ComObject Shell.Application
$volume = $shell.Namespace(17).ParseName(('{0}:' -f $letter))
if (-not $volume) { throw "Explorer could not find the SD volume." }
$volume.InvokeVerb('Eject')
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 250
    if (-not $drive.IsReady) { Write-Output "Ejected Model 12 SD ${letter}:"; return }
}
throw "The Model 12 card is still accessible. Leave STORAGE active."
