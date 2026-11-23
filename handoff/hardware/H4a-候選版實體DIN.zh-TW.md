# 電腦產生 MTC 經實體 DIN 的候選版重測

Model 12 韌體 1.50 0103；程式 f13949d9（#1669 + #1663 起音候選 + #1634 I24），48 kHz／256。每組十次，回送極差門檻 3 ms，另核對二十次停止定位與完整 MIDI 封包。選用每組第一筆環境和封包均有效的紀錄。門檻未過的有效量測照樣列入。

| 格率 | 方向 | 舊回送極差 ms | 新回送極差 ms | 新輸出極差 ms | 新回送首音中位 ms（相對主機標籤） | 中位數相對舊版 ms | 判定 |
|---|---|---:|---:|---:|---:|---:|---|
| 24 | UM-ONE → Model 12 | 3.293 | 1.311 | 1.357 | 181.556 | +1.943 | [通過](runs/home-20261122-234047-din-24-forward/result.json) |
| 24 | Model 12 → UM-ONE | 4.952 | 1.067 | 2.016 | 181.694 | +2.375 | [通過](runs/home-20261122-234238-din-24-reverse/result.json) |
| 25 | UM-ONE → Model 12 | 4.302 | 0.292 | 1.130 | 175.582 | +3.370 | [通過](runs/home-20261122-234811-din-25-forward/result.json) |
| 25 | Model 12 → UM-ONE | 3.974 | 2.017 | 2.006 | 175.100 | +1.055 | [通過](runs/home-20261122-235002-din-25-reverse/result.json) |
| 29.97df | UM-ONE → Model 12 | 4.285 | 1.193 | 1.711 | 150.364 | +1.518 | [通過](runs/home-20261122-235153-din-29.97df-forward/result.json) |
| 29.97df | Model 12 → UM-ONE | 4.126 | 1.224 | 1.584 | 150.675 | +2.885 | [通過](runs/home-20261122-235345-din-29.97df-reverse/result.json) |
| 29.97nd | UM-ONE → Model 12 | 5.857 | 1.040 | 1.230 | 150.626 | +2.151 | [通過](runs/home-20261123-003704-din-29.97nd-forward/result.json) |
| 29.97nd | Model 12 → UM-ONE | 4.839 | 1.096 | 1.347 | 150.526 | +2.059 | [通過](runs/home-20261123-003853-din-29.97nd-reverse/result.json) |
| 30 | UM-ONE → Model 12 | 5.015 | 2.004 | 2.019 | 150.770 | +1.238 | [通過](runs/home-20261122-233258-din-30-forward/result.json) |
| 30 | Model 12 → UM-ONE | 5.105 | 1.515 | 1.151 | 150.218 | +2.507 | [通過](runs/home-20261122-233258-din-30-reverse/result.json) |

## 全部嘗試

目前有 10/10 組具有效環境及相符封包，其中 10 組通過全部原門檻。

- [home-20261122-233258-din-24-forward](runs/home-20261122-233258-din-24-forward/)　[{"tag": "take-4:locate-frame-48", "sent": "f07f7f010100000200f7", "received": "f07f7f01010000020000f7"}]；回送極差 177.9154 ms

- [home-20261122-233258-din-24-reverse](runs/home-20261122-233258-din-24-reverse/)　Busy system during run (77.1%)；回送極差 0.3846 ms

- [home-20261122-234429-din-25-forward](runs/home-20261122-234429-din-25-forward/)　[{"tag": "take-10:stopped-frame-250", "sent": "f07f7f010120000a00f7", "received": "f07f7f00010120000a00f7"}]；回送極差 1.1078 ms

- [home-20261122-234620-din-25-forward](runs/home-20261122-234620-din-25-forward/)　[{"tag": "take-8:locate-frame-50", "sent": "f07f7f010120000200f7", "received": "f07f7f01012000020000f7"}]；回送極差 170.9904 ms

- [home-20261122-235535-din-29.97nd-forward](runs/home-20261122-235535-din-29.97nd-forward/)　[{"tag": "take-10:stopped-frame-300", "sent": "f07f7f010160000a00f7", "received": "f07f7f00010160000a00f7"}]；回送極差 6.3261 ms

- [home-20261122-235726-din-29.97nd-forward](runs/home-20261122-235726-din-29.97nd-forward/)　環境紀錄無法解碼，原檔保留。

- [home-20261122-235917-din-29.97nd-forward](runs/home-20261122-235917-din-29.97nd-forward/)　擷取未完成，缺少結束環境與有效量測。

- [home-20261123-001752-din-29.97nd-forward](runs/home-20261123-001752-din-29.97nd-forward/)　Measurement process exited 120；回送極差 1.2046 ms

已完成組別的原始資料含原生 ASIO 時間戳、輸出與 USB 回送 PCM、收發 MIDI、起音辨識與完整環境。首音中位數是同樣樂譜上的偏差，不能當作按鍵到聲音的單向延遲；不同次實機測量包含輸出及回送路徑的自然變動。

[逐組回呼直方圖、封包及新舊數字](runs/h4a-home-prep/physical-matrix.json) · [離線診斷](起音與往返複查.zh-TW.md) · [異常封包、USB 回送與系統重開機](H4a-異常與重開機紀錄.zh-TW.md)
