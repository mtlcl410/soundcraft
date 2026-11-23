from pathlib import Path
p=Path(r'E:/soundcraft/compatibility-audit/g11-hardware/ROUND4-ACCEPTANCE.zh-TW.md')
s=p.read_bytes()
old='| 1 歌頭 | 待測 | 待測 | 待測 | 待測 | 待測 | — |'.encode()
new='| 1 歌頭 | 00:00:00:00／SD 69.552 s | DIN 與 USB 各 8,344 筆 QF | 鎖定跟播、跟停至 00:01:09:16；錄音旗標全程 false，輪詢無錯誤 | CH2 的 A4 5.0000／5.0135 s | +13.5 | — |'.encode()
assert s.count(old)==1
old2='三輪極差、量測解析度與最終判定待填。'.encode()
new2='第一輪歌曲 `040208_0004` 的 CH1 麥克風與 CH2 PC 回送各有 3,338,496 個 48 kHz／24-bit 取樣。5 秒附近，CH2 的主音在 440.92 Hz；以 1 ms RMS 視窗判定起音，正值表示伴奏落後於歌曲位置。SD 與本機副本逐檔核對 SHA-256。[SD 檔案清單](h-mtc-sd-20261121-211205/take1-sd.json) · [起音分析](h-mtc-sd-20261121-211205/take1-audio.json) · [線上時碼與走帶摘要](h-mtc-sd-20261121-211205/take1-summary.txt)。三輪極差與最終判定待填。'.encode()
assert s.count(old2)==1
p.write_bytes(s.replace(old,new).replace(old2,new2))
