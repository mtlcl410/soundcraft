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
 Start-Headers usbprobe
 try {Start-Sleep -Seconds 5} finally {Stop-Headers usbprobe}
 New-Item probe-saved.signal -ItemType File | Out-Null
 Wait-Flag 'probe-decoded.signal' 180
 $counts=Get-Content native-counts-usbprobe.txt
 if (!($counts -match '^\{(30E1D284|36DA592D|AC52AD17)')){throw 'Windows wrote no xHCI / UCX / USBHUB3 events to the standalone ETL. No further recordings started.'}
 New-Item probe-ok.signal -ItemType File | Out-Null
 foreach($size in 64,128){
   $tag="usb$size"
   Wait-Flag "request-$tag.signal" 900
   Start-Headers $tag
   try {
    & wpr -start "$PSScriptRoot\ScheduleOnly.wprp!SoundCraftGap" -filemode -instancename SoundCraftUSBRetry *> "$tag-wpr-start.log"
    if($LASTEXITCODE){throw 'WPR start failed'}
    try {New-Item "ready-$tag.signal" -ItemType File|Out-Null;Wait-Flag "end-$tag.signal" 660}
    finally {& wpr -stop "$PSScriptRoot\kernel-$tag.etl" -instancename SoundCraftUSBRetry *> "$tag-wpr-stop.log"}
   } finally {Stop-Headers $tag}
 }
} catch {$_ |Out-String|Set-Content usbprobe-result.log; exit 1}

