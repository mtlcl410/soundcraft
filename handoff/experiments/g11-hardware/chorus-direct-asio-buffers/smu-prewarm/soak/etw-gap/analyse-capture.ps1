param([int]$Samples,[string]$Tag)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
function Verify-Exit(){if($LASTEXITCODE){throw "Step failed with exit code $LASTEXITCODE"}}
$case=Join-Path .. $Tag
$procId=(Get-Content (Join-Path $case 'control.json') -Raw|ConvertFrom-Json).pid
python -X utf8 windows.py $Samples $Tag
Verify-Exit
python -X utf8 landmark.py $Samples $Tag *> "landmark-$Tag.log"
& ./UsbEvents.exe $Tag
Verify-Exit
dotnet Decode/bin/Release/net8.0/Decode.dll $Tag $procId
Verify-Exit
python -X utf8 partition.py $Samples $Tag *> "partition-$Tag.log"
Verify-Exit
python -X utf8 stages.py $Tag *> "stages-$Tag.log"
Verify-Exit
python -X utf8 usb-evidence.py $Tag *> "usb-evidence-$Tag.log"
Verify-Exit

