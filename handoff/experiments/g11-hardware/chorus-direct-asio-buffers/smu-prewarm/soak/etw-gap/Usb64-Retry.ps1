$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
function Wait-Flag($name,$seconds){
 $until=(Get-Date).AddSeconds($seconds)
 while(!(Test-Path -LiteralPath $name)){if((Get-Date) -gt $until){throw "Timeout: $name"};Start-Sleep -Milliseconds 350}
}
function Start-Headers($tag){
 $session="SoundCraftUSBHeaders-$tag"
 $file=Join-Path $PSScriptRoot "trace-$tag.etl"
 if(Test-Path $file){throw "Existing $file"}
 & logman create trace $session -pf (Join-Path $PSScriptRoot 'Usb-Headers-providers.txt') -o $file -bs 256 -nb 64 256 -ets *> "$tag-start.log"
 if($LASTEXITCODE){throw "USB ETW start failed: $LASTEXITCODE"}
}
function Stop-Headers($tag){
 & logman query "SoundCraftUSBHeaders-$tag" -ets *> "$tag-status.log"
 & logman stop "SoundCraftUSBHeaders-$tag" -ets *> "$tag-stop.log"
 if($LASTEXITCODE){throw "USB ETW stop failed: $LASTEXITCODE"}
}
try {
  Wait-Flag 'stream-usb64r.signal' 180
  Start-Headers usb64r
  try {
    & wpr -start "$PSScriptRoot\ScheduleOnly.wprp!SoundCraftGap" -filemode -instancename SoundCraftUSB64Retry *> usb64r-wpr-start.log
    if($LASTEXITCODE){throw 'WPR start failed'}
    try {New-Item 'ready-usb64r.signal' -ItemType File|Out-Null; Wait-Flag 'end-usb64r.signal' 600}
    finally {& wpr -status collectors -details -instancename SoundCraftUSB64Retry *> usb64r-kernel-status.log; & wpr -stop "$PSScriptRoot\kernel-usb64r.etl" -instancename SoundCraftUSB64Retry *> usb64r-wpr-stop.log}
  } finally {Stop-Headers usb64r}
} catch {$_|Out-String|Set-Content usb64r-error.log; exit 1}
