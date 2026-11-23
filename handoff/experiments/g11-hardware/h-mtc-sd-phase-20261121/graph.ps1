Add-Type -AssemblyName System.Windows.Forms.DataVisualization
Add-Type -AssemblyName System.Drawing
$c = New-Object System.Windows.Forms.DataVisualization.Charting.Chart
$c.Width=1250
$c.Height=690
$c.BackColor=[Drawing.Color]::White
$font='Microsoft JhengHei'
$area = New-Object System.Windows.Forms.DataVisualization.Charting.ChartArea
$area.Name='takes'
$area.AxisX.Minimum=10
$area.AxisX.Maximum=21
$area.AxisX.Interval=1
$area.AxisX.IsMarginVisible=$false
$area.AxisX.MajorGrid.Enabled=$false
$area.AxisX.Title='Model 12 的 SD 歌曲末碼'
$area.AxisX.LabelStyle.Format='0000'
$area.AxisY.Minimum=0
$area.AxisY.Maximum=65
$area.AxisY.Interval=10
$area.AxisY.Title='A4 相對排定位置的延遲（ms）'
$area.AxisY.MajorGrid.LineColor=[Drawing.Color]::Gainsboro
foreach($axis in @($area.AxisX,$area.AxisY)){ $axis.TitleFont=New-Object Drawing.Font($font,13); $axis.LabelStyle.Font=New-Object Drawing.Font($font,12)}
$c.ChartAreas.Add($area)
$legend=New-Object System.Windows.Forms.DataVisualization.Charting.Legend
$legend.Docking='Bottom'
$legend.Alignment='Center'
$legend.Font=New-Object Drawing.Font($font,12)
$c.Legends.Add($legend)
$r=(Get-Content distribution.json -Raw -Encoding utf8 | ConvertFrom-Json).rows
foreach($spec in @(@('SD 伴奏軌（相對歌曲時間）','sd','#004884','Circle'),@('Windows 播放端（相對 DIN）','render','#C85018','Diamond'))){
 $s=New-Object System.Windows.Forms.DataVisualization.Charting.Series($spec[0])
 $s.ChartType='Point'
 $s.Color=[Drawing.ColorTranslator]::FromHtml($spec[2])
 $s.MarkerStyle=$spec[3]
 $s.MarkerSize=12
 $s.ChartArea='takes'
 foreach($row in $r){$value=$row.($spec[1]); if($null -ne $value){[void]$s.Points.AddXY([int]$row.song.Substring(7),[double]$value)}}
 $c.Series.Add($s)
}
$title=$c.Titles.Add('十次 MTC 跟播：跨次延遲在 Windows 播放端已可見')
$title.Font=New-Object Drawing.Font($font,22,[Drawing.FontStyle]::Bold)
$subtitle=$c.Titles.Add('同一個 5.000 秒 A4  •  0011–0015 從歌頭起錄  •  0016–0020 從第 2 秒起錄')
$subtitle.Font=New-Object Drawing.Font($font,13)
$foot=$c.Titles.Add('0016 只有 SD 錄音。九次完整對照的播放端極差為 43.59 ms；十次 SD 極差為 42.88 ms。')
$foot.Font=New-Object Drawing.Font($font,12)
$foot.Docking='Bottom'
$c.SaveImage((Join-Path $PWD 'ten-takes.png'),'Png')
$c.Dispose()
