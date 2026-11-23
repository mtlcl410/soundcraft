from pathlib import Path
p=Path(r'E:/soundcraft/compatibility-audit/g11-hardware/ROUND4-ACCEPTANCE.zh-TW.md')
with p.open('r',encoding='utf8',newline='') as f: text=f.read()
nl='\r\n' if '\r\n' in text else '\n'
anchor='**設定紀錄。**'
assert text.count(anchor)==1
add='**本輪預檢（2026-11-21）。** 操作者讀回 Model 12 韌體 **1.30 0088**。使用 #1663 的 Windows 桌面版 `ee80920` 和 S‑MU2000 鋼琴專案的測試副本。程式回報 48 kHz／24-bit、30 fps non-drop、起始時碼與外部偏移均為零、Frames 8、Gen MTC 關閉。UM-ONE 與 Model 12 USB MIDI 都能開埠，讀取器已選 UM-ONE。預檢時本體尚未開始本輪 SD 錄音。[執行檔及專案雜湊](h-mtc-sd-20261121-211205/control.json) · [設定讀回](h-mtc-sd-20261121-211205/reader-arm.json) · [WinMM 開埠](h-mtc-sd-20261121-211205/port-check.log)'
with p.open('w',encoding='utf8',newline='') as f:f.write(text.replace(anchor,add+nl+nl+anchor))
