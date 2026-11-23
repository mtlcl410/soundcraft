param(
 [Parameter(Mandatory=$true)][string]$CargoLog,
 [Parameter(Mandatory=$true)][string]$Destination,
 [string]$TestName="six_hour_clock_history_has_bounded"
)
$match=[regex]::Match((Get-Content -Raw -LiteralPath $CargoLog),'Running unittests[^\r\n]*\((.+?\.exe)\)')
if (!$match.Success) {throw "No test binary in log $CargoLog"}
$start=[System.Diagnostics.ProcessStartInfo]::new()
$start.FileName=$match.Groups[1].Value
$start.UseShellExecute=$false
$start.CreateNoWindow=$true
$start.RedirectStandardOutput=$true
$start.RedirectStandardError=$true
foreach ($arg in @($TestName,'--ignored','--nocapture','--test-threads=1')) {$start.ArgumentList.Add($arg)}
$p=[System.Diagnostics.Process]::Start($start)
$out=$p.StandardOutput.ReadToEndAsync()
$err=$p.StandardError.ReadToEndAsync()
[long]$peak=0
while (!$p.HasExited) {
 $p.Refresh()
 try { $peak=[Math]::Max($peak,$p.PeakWorkingSet64) } catch [System.InvalidOperationException] {}
 [void]$p.WaitForExit(25)
}
$p.WaitForExit()
@($out.Result,$err.Result,"Measured whole test process peak working set bytes=$peak (Windows; includes host/test-device/library baseline). ExitCode=$($p.ExitCode)") | Set-Content -LiteralPath $Destination -Encoding utf8
exit $p.ExitCode
