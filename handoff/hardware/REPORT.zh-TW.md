# G-11 實機驗收（Model 12 韌體 1.50 0103）

**11 月 23 日集中實測。** main 的停止後 ASIO 自動恢復已通過三次真實 STORAGE；本體 MTC 三遍的首音極差 211.819 ms 超過 3 ms。舊版各項原始成績依日期保留。[STORAGE 實測](ASIO-storage-idle-recovery.zh-TW.md) · [本體跟播](本體三次跟播-20261123.zh-TW.md)

**先前的環境診斷。** 退出 STORAGE 後的 ASIO 回呼異常只供環境診斷；下列原始門檻判讀保留為當時量測紀錄。[驅動版本、main 對照、回呼分布及 #1663 重新定位判定](ASIO-environment.zh-TW.md)

更新於 2026-11-22T21:35:52+08:00。操作員確認本機、48/24、OUTPUT DELAY 為 DISABLE，USB 路由經面板照片核對。Windows 重插後同時列出 Model 12 與 UM-ONE。各輪環境紀錄與原始 PCM／事件檔在 [runs](runs/)。

| PR | 實測用程式碼基準 | 規定項目 |
|---|---|---|
| #1662 | 8fd15068 | H-1、H-2、H-3 |
| #1663 | bab99312 | H-4 |
| #1669 | 33dfa5f5 | H-5、H-6、H-7、H-9 |
| 三支 | 上列版本 | H-8、H-10 |

## M-1　USB 1/2 經 CH9/10 回錄

同一 ASIO callback 觀測輸出 1、輸入 9，使用每次六個不同的低振幅脈衝序列，逐個互相關。驗證 ASIO 連續取樣位置與回呼序號，每個緩衝目標獨立開串流 20 次。48 kHz，通過門檻為極差 ≤ 1 取樣。差額為實測減驅動回報，保留正負號。

| 量測組 | 緩衝 | 有效次數 | 往返取樣 | 極差 | 回報輸入 + 輸出 | 差額 | 判定 |
|---|---:|---:|---:|---:|---:|---:|---|
| m1-independent-128-a | 128 | 20 | 611–616 | 5 | 176 + 481 | -46 至 -41 | 未達門檻 |
| m1-independent-256-a | 256 | 20 | 987–993 | 6 | 304 + 728 | -45 至 -39 | 未達門檻 |
| m1-independent-512-c | 512 | 20 | 1710–1721 | 11 | 560 + 1205 | -55 至 -44 | 未達門檻 |
| m1-integration-128-formal-01 | 128 | 20 | 611–616 | 5 | 176 + 481 | -46 至 -41 | 未達門檻 |
| m1-integration-256-formal-01 | 256 | 20 | 987–991 | 4 | 304 + 728 | -45 至 -41 | 未達門檻 |
| m1-integration-512-formal-01 | 512 | 20 | 1715–1721 | 6 | 560 + 1205 | -50 至 -44 | 未達門檻 |

## SoundCraft 目前版本的 ASIO 狀態

#1662 的 8fd15068 已實際啟動並透過正常音訊設定指令選取 Model Mixer ASIO。128、256、512 取樣全部退到靜音，三份 application.log 都記錄 unsupported device sample format I24，相同連線上的獨立播放器有聲音資料。Packed I24 由尚未合併的 [#1634](https://github.com/storytold/soundcraft/pull/1634) 處理。原 head 下可報告啟動失敗，無法計算 SoundCraft 音訊往返。此結果及獨立基準已放入 [#1662 實機留言](https://github.com/storytold/soundcraft/pull/1662#issuecomment-7078832958)。[測法與無效嘗試說明](前置紀錄.zh-TW.md)

## M-2　雙向 DIN 延遲

原始 QPC 從主機送出呼叫到另一介面輸入回呼。每個方向單獨計時，各自 10,000 個 F8；jitter 為相對中位延遲的絕對差。初探每方向各 4 個，兩向均經一般 Model 12 MIDI 埠全部到達；MIDIIN2／MIDIOUT2 均為 0/4。原始檔在 [routes.json](runs/m2-identify-a/routes.json)。

| 實際方向 | F8 數 | median ms | p99 ms | max ms | jitter median / p99 / max ms |
|---|---:|---:|---:|---:|---:|
| UM-ONE 1 → Model 12 MIDI 1 | 10000 | 0.5972 | 0.7966 | 2.4840 | 0.0186 / 0.1994 / 1.8868 |
| Model 12 MIDI 2 → UM-ONE 0 | 10000 | 0.6563 | 0.8815 | 2.1138 | 0.0216 / 0.2251 / 1.4574 |

## 待驗項目

各項結果依下方實測記錄更新。H-1、H-2、H-3a、H-4a、H-5～H-10 仍需完整驗收。H-6 的錄音差額及追蹤 issue 草稿須待實測；H-8 目前不能填入 SoundCraft 排程誤差。SD、選用的 PC1X 和 USB 拔插集中在一次手動操作。

## 無效嘗試

- h10-physical-relay-pilot-01：Measurement process exited 1, Missing actual driver settings: device-end.json。
- h3b-model12-01：Competing build, remote session or endpoint change during run, Busy system during run (76.3%), Busy system during run (75.1%), Busy system during run (76.6%)。
- h4b-model12-01：Measurement process exited 1, Missing actual driver settings: device-end.json。
- m1-independent-512-a：Measurement process exited 1, Missing actual driver settings: device-start.json, Missing actual driver settings: device-end.json。
- m1-independent-512-b：Busy system during run (86.7%)。
- m1-integration-follow-probe-01：Measurement process exited 1, Missing actual driver settings: device-start.json, Missing actual driver settings: device-end.json。
- m1-route-128-01：Measurement process exited 1, Missing actual driver settings: device-start.json, Missing actual driver settings: device-end.json。
- m1-soundcraft-128-a：Measurement process exited 1, Missing actual driver settings: device-start.json, Missing actual driver settings: device-end.json。
- m1-soundcraft-256-a：Measurement process exited 1, Missing actual driver settings: device-start.json, Missing actual driver settings: device-end.json。
- m1-soundcraft-512-a：Measurement process exited 1, Missing actual driver settings: device-start.json, Missing actual driver settings: device-end.json。
- m2-forward-a：Measurement process exited 1。
- m2-forward-b：Busy system during run (92.4%)。
- m2-reverse-a：Busy system during run (77.4%)。
- storage-main-85623f28-01：Missing actual driver settings: device-start.json, Missing actual driver settings: device-end.json。

## 本機整合 #1634 的驗證

三個獨立本機 merge 各自保留原 PR 和 #1634 的來源，見 [整合提交對照](integrations.json)。本次實機使用最上層整合版本 `f561a57a`，包含 #1662、#1663、#1669 和 #1634 的 ASIO I24 支援。[本機執行檔 SHA-256](audio/build/f561a57a-build.json)

| 項目 | 實際觀察 | 用途 |
|---|---|---|
| ASIO 256 取樣預演 | 輸出 1 至輸入 9 的六個識別脈衝，相關係數均為 1.0，全部相距 989 個取樣。錄完後測試工具立刻重新指定使用中的 ASIO 裝置時失敗，該輪排除於正式統計。 | 驗證接線與 I24 方向。[原始紀錄](runs/m1-integration-follow-probe-01/) |
| DIN 時碼與音訊共同擷取預演 | 修正測試專案的開始時碼為 00:00:00:00 後，收到 960 個 quarter-frame。16 個相異聲音標記全部在 ASIO 輸出與 CH9 回送找到。 | 確認實機操作前的擷取工具。[標記逐筆對照](runs/h4-integration-chain-pilot-02/marker-phase.json) |
| 集中操作順序 | 操作員沒有指定長度的 48/24 歌曲。先錄 M-3，再用新錄的 SD 歌曲做 H-4b。首次 H-4b 等待操作的空錄不計入結果。 | 保留原規定的長度、定位點和通過門檻。 |

### H-4b　Model 12 播放 040209_0002，經 DIN 追隨 MTC

三次操作均完成，環境檢查有效。時碼以 30 fps 依每組八個 quarter-frame 解碼，以下列出收到第一段完整標籤的位置。音訊偏差以每輪 DIN 標籤推得的時間軸為基準，在 ASIO 輸出 1 和 CH9 回送找相同的已知波形；數值包含該路徑延遲。三次首個標記在兩路的相關係數均為 1.0。

| 本體起播 | 第一個完整標籤 | 實際發碼秒數 | QF 數 | 首個標記（曲中秒） | 輸出偏差 ms | CH9 回送偏差 ms | 兩路均找到／預期 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 歌頭 | 第 2 格 | 70.856 | 8,504 | 0.25 | +195.780 | +215.732 | 141／142 |
| 歌頭 | 第 2 格 | 70.589 | 8,472 | 0.25 | +196.727 | +216.548 | 140／141 |
| 第 30 秒 | 第 902 格 | 70.922 | 8,512 | 30.25 | +196.701 | +217.523 | 141／142 |

首個標記在回送端的三次極差為 **1.791 ms**，低於預定的 3 ms。這項數字衡量重複性；三次回送的首個起音仍各晚約 216–218 ms。M-3 的 SD 和 ASIO 輸出比對跨越 608 秒，標記間距差為零。[逐一標記與線上時碼](runs/h4b-model12-02/marker-phase.json) · [環境驗證](runs/h4b-model12-02/environment-result.json)

三輪均重新定位一次。曲中 1.25 秒（前兩輪）與 31.25 秒（第三輪）的短標記完全落在跳過的區間，兩路 PCM 都只有前後相鄰標記。原 #1663 的離線重播得到同一行為，符合 master 位置優先的規則。三次重新定位時回呼節奏均正常。本機報告另列跨越落點的持續 MIDI 音符限制。[環境診斷與行為判定](ASIO-environment.zh-TW.md) · [相鄰起音對照](runs/h4b-model12-02/unmatched-marker-neighbours.json) · [逐筆診斷](runs/h4b-model12-02/transport.jsonl)


### H-3b　USB STORAGE 三次退出後的 A4

整合版同一程序完成三輪，操作員每次回到歌曲後都保持停止。Windows 已逐次安全退出 SD 卡。跨越 STORAGE 的環境檢查判定這組**無效，只供診斷**。Windows 在操作途中曾切換預設播放端點，三輪 CPU 各有一個取樣超過 75%（76.3%、75.1%、76.6%）。全程沒有偵測到編譯程序或遠端桌面。正式的 3 ms 恢復條件待重測。

| 量測 | DIN quarter-frame | 預期 A4 前後各一秒的 ASIO 回呼數 | 回呼間隔中位數 | CH9 回送 A4 偏差 |
|---|---:|---:|---:|---|
| 進 STORAGE 前 | 960 | 375 | 5.016 ms | +5.478 ms |
| 第一次退出 | 960 | 8 | 251.285 ms | 無可辨認起音 |
| 第二次退出 | 960 | 8 | 251.356 ms | 無可辨認起音 |
| 第三次退出 | 960 | 8 | 251.442 ms | 無可辨認起音 |

三次均未操作 SoundCraft 的 Reconnect。時碼輸入在三輪都能接收完整的測試訊息；擷取視窗缺少連續的雙向 PCM，無法判定喇叭聲音或計算恢復後偏差。現有結果不足以歸因於原 PR 或驅動。[時序證據](runs/h3b-model12-01/cycle-summary.json) · [環境檢查](runs/h3b-model12-01/environment-result.json) · [#1662 留言](https://github.com/storytold/soundcraft/pull/1662#issuecomment-7079494772) · [#1663 跟播與 SD 留言](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7079494514)

### 1.30 與 1.50 的比較條件

操作員先前在同一台 Model 12 讀到 **1.30 0088**，本輪所有實測均在更新、重開機並確認 **1.50 0103** 後進行。1.40 新增電腦 USB 1/2 回送到 CH9/10 或 MAIN 的路由；1.41 修正 CH1–8 的 USB 輸出 gain boost；1.50 支援 Settings Panel 的 meter bridge，並將 LCD 的 MAIN 取樣點移到 MAIN 推桿前。1.42 和 1.50 都列有穩定性改善；原廠未具體列出 MTC、F8、ASIO 裝置恢復的時序調整。[TASCAM 發行說明](https://cf.tascam.com/wp-content/uploads/downloads/products/tascam/model_12/e_model12_rn_vl.txt)

舊版三輪錄音讀的是 SD 上曲中第 5 秒的 S-MU2000 A4；本輪 H-4b 讀的是起播後 0.25 秒的編碼脈衝，透過原廠 ASIO 輸出 1 與 USB 輸入 9 回錄，軟體也改用含 #1634 的本機組合。舊數字與本輪首音的絕對延遲及跨次極差不可相減來估算韌體影響。舊 STORAGE 測試使用共享音訊端點，本輪使用 ASIO，而且本輪 STORAGE 期間環境改變，三次只供診斷。離線軟體回歸測試不依賴 Model 12 韌體。保留原始舊報告，所有後續數據繼續標註韌體與路徑。[舊版 SD／MTC 量測](../g11-hardware/h-mtc-sd-phase-20261121/REPORT.zh-TW.md) · [韌體更新紀錄](firmware/準備紀錄.md)

## M-3　SD 錄音與 USB 同步回錄

測試使用 Model Mixer ASIO、48 kHz、256 取樣。操作員確認 CH9/10 的 REC 燈常亮且本體計數前進。電腦記錄的環境為有效。輸出 1 辨認到 609 個已知標記，輸入 9 辨認到 609 個。兩端共同辨認 609 個，首末間隔 607.999250 秒，往返 945–981 取樣。量測區間的 ASIO 取樣位置中斷 0 次，回呼序號中斷 0 次。[逐標記檢查摘要](runs/m3-sd-01/pc-markers.json)

SD 與 USB 共同標記 609 個，跨越 608.000000 秒。SD 減 USB 的首末間距差 +36 取樣（+1.234 ppm），與 Windows QPC 的端點差折合 +38.348 ppm。SD 和 USB 來自同一台 Model 12；QPC 端點亦包含回呼到達抖動。[SD 與 USB 配對](runs/m3-sd-01/sd-drift-pairs.csv)

逐一比對全部 609 個標記，SD 對 ASIO 輸出 1 的相對距離極差為 0 取樣。SD 對 USB 輸入 9 的距離變動發生在標記 44（+12）, 56（+6）, 65（+6）, 76（+6）, 414（+6），括號內為取樣數。首末差換算的 ppm 是全段平均值，五次跳變的原因尚待確認。[SD 原檔校驗](runs/m3-sd-01/sd/040209_0002/manifest.json)

## H-4a　電腦產生 MTC，經實體 DIN 跟播

每格率、每方向各十次，從零和非零位置交替起播。起音取 USB 輸入 9 的編碼波形，時碼以另一介面實收的 quarter-frame 解碼。極差門檻為 3 ms。相對產生端的校正起音為回錄起音減去 M-1 的往返中位數，再加上該方向 M-2 的傳輸中位數；常數校正不會改變極差。

| 格率 | DIN 傳送端 → 接收端 | 有效起音／預期 | 定位錯誤／檢查 | QF 計數異常的段數 | 校正起音中位 ms | 極差 ms | 判定 |
|---|---|---:|---:|---:|---:|---:|---|
| 24 | UM-ONE → Model 12 | 10/10 | 0/20 | 0 | 159.575 | 3.293 | [未達門檻](runs/h4a-integration-24-forward-01/result.json) |
| 24 | Model 12 → UM-ONE | 10/10 | 0/20 | 0 | 159.339 | 4.952 | [未達門檻](runs/h4a-integration-24-reverse-01/result.json) |
| 25 | UM-ONE → Model 12 | 10/10 | 0/20 | 0 | 152.174 | 4.302 | [未達門檻](runs/h4a-integration-25-forward-01/result.json) |
| 25 | Model 12 → UM-ONE | 10/10 | 0/20 | 0 | 154.066 | 3.974 | [未達門檻](runs/h4a-integration-25-reverse-01/result.json) |
| 29.97df | UM-ONE → Model 12 | 10/10 | 0/20 | 0 | 128.808 | 4.285 | [未達門檻](runs/h4a-integration-29.97df-forward-01/result.json) |
| 29.97df | Model 12 → UM-ONE | 10/10 | 0/20 | 0 | 127.812 | 4.126 | [未達門檻](runs/h4a-integration-29.97df-reverse-01/result.json) |
| 29.97nd | UM-ONE → Model 12 | 10/10 | 0/20 | 0 | 128.437 | 5.857 | [未達門檻](runs/h4a-integration-29.97nd-forward-01/result.json) |
| 29.97nd | Model 12 → UM-ONE | 10/10 | 0/20 | 0 | 128.488 | 4.839 | [未達門檻](runs/h4a-integration-29.97nd-reverse-01/result.json) |
| 30 | UM-ONE → Model 12 | 10/10 | 0/20 | 0 | 129.494 | 5.015 | [未達門檻](runs/h4a-integration-30-forward-01/result.json) |
| 30 | Model 12 → UM-ONE | 10/10 | 0/20 | 0 | 127.731 | 5.105 | [未達門檻](runs/h4a-integration-30-reverse-01/result.json) |

同一路徑上各次起音的散布包含 USB 傳輸、鎖定、ASIO 回呼與回送的不確定性。失去發送介面時的三種 Freewheel 行為另行驗收。

## SoundCraft 閒置時自動恢復 ASIO

[回歸測試、修正歸屬與 Model 12 三輪 STORAGE 驗收](ASIO-storage-idle-recovery.zh-TW.md)

## H-4a　起音極差的離線重播與修正

[100 段 PCM 重播、四種緩衝、修正前後數值及剩餘門檻](H4a-MTC-anchor-phase.zh-TW.md)

## 回家前複查與集中驗收

[起音與往返複查、三支 PR 的自動驗證](起音與往返複查.zh-TW.md) · [同一次到場的面板步驟](回家實測清單.zh-TW.md)

[候選版實體 DIN 的十組數字](H4a-候選版實體DIN.zh-TW.md) · [異常封包、USB 回送與系統重開機](H4a-異常與重開機紀錄.zh-TW.md)

## 2026-11-23 集中面板實測

[三遍本體跟播與起音超標](本體三次跟播-20261123.zh-TW.md) · [三輪 STORAGE 自動恢復與 A4 回送](ASIO-storage-idle-recovery.zh-TW.md)


[夜間效能複查與長測狀態](夜間效能複查-20261123.zh-TW.md)
