# 樂團表演情境自動驗收 · 2026-11-22

在 Windows 上用 #1669 的整合版驗證 #1662 的 Beat Clock 輸出、#1663 的 MTC 收發和 #1669 的 Beat Clock 跟隨。找到並修正一項可重現的副歌變速問題。下表的數字取自修正後的回錄。

| 情境 | 操作與結果 | 紀錄 |
| --- | --- | --- |
| 副歌重來 | 120 BPM，Continue 前送 SPP 64（8.000 秒），銅鈸只響一次；改送 SPP 65（8.125 秒），銅鈸零次。後續分別有 3、5 下小鼓，兩遍都跟停。 | [8.000 秒](exact-final-result.json) · [8.125 秒](panel-first-result.json) · [回錄 WAV](exact-final.wav) |
| 同一份伴奏改速度 | 原八小節 S-MU2000 伴奏在 120、100 BPM 都有八下小鼓、一聲副歌銅鈸和末小節踩鈸。對應長度 16.0、19.2 秒。 | [120 BPM](tempo-120-result.json) · [100 BPM](tempo-b-result.json) |
| 兩台定序器合奏 | 兩個 SoundCraft 程序，一個打鼓並發 Clock，一個依 Clock 彈 S-MU2000 貝斯。第 5 小節加速或減速，整首均有 32 下鼓、64 個貝斯起音。從副歌重來均有 16 下鼓、32 個貝斯起音。另用有明確起音的打擊樂量化偏差，見下節。 | [減速](fixed-ensemble-120-100-top-results.json) · [加速](fixed-ensemble-100-120-top-results.json) · [從副歌起播](fixed-ensemble-120-100-chorus-results.json) |
| 斷鐘時繼續合奏或停錄 | 經實體 DIN 中斷 Clock 1.1 秒，Coast 繼續走帶，Stop on loss 停止，重新定位後兩者皆能以 100 BPM 繼續。輸入音訊與 MIDI 的軟體回歸另驗證 Coast 保留跨斷鐘的 25,200 個取樣和 3 個音，Stop on loss 收錄至逾時前的 12,000 個取樣和 1 個音。 | [實體 MIDI](physical-clock-loss/summary.json) · [錄音測試](../band-overnight-20261122/recording-tests.log) |
| 鋼琴跟隨 MTC 定位 | 在 30 fps 依序從第 0、2、5、5、5 秒起播。前兩遍都有 C4、A4、F♯5；三遍 5 秒起播都是 A4、F♯5，相隔 0.500 秒。停止後均無額外起音。 | [五次音高、間隔與封包數](piano-results.json) · [第 5 秒起播 WAV](piano-2.wav) |
| MTC 遺失與燈光定位 | 模擬中斷，None 約 84 ms、Frames 8 約 273 ms 時觀察到停止（含輪詢時間），Jam Sync 跨過 10 秒仍播放，三種均在恢復後重新鎖定。模擬燈控接收器在停止中收到 8 秒與 12 秒的 full-frame，播放中解出 33 組連續前進的 quarter-frame 組。 | [None](freewheel-none.json) · [Frames 8](freewheel-frames.json) · [Jam Sync](freewheel-jam_sync.json) · [燈光定位](lighting-cues.json) |

## 第五小節變速的拍點

發碼端與跟隨端在同一台 Windows 電腦執行，經 Model 12 USB MIDI → 實體 DIN OUT → Roland UM-ONE 傳輸。兩者的打擊樂各占數位回錄的一個聲道。以 48 kHz 原始取樣的起音做正規化相關比對，門檻 0.85。每遍先算第 5 至 14 拍的跟隨端相對偏差中位數，再從第 18 拍（第 5 小節第 2 拍）扣除此基準。負值代表跟隨端較早，正值代表較晚。

| 第五小節速度 | 修正前（各一遍） | 修正後（各三遍，依序） |
| --- | ---: | ---: |
| 120 → 100 BPM | −98.68 ms | −28.48、−41.79、−34.46 ms |
| 100 → 120 BPM | +59.09 ms | +24.54、+26.78、+33.15 ms |

修正後六遍的末四拍中位偏差均回到原穩態的 0.73–4.04 ms 之內。兩個程序從停止到第一個打擊樂起音仍相差 40–50 ms；這是另外量到的起播時間。實體結果適用於此組裝置與輸出設定。

![修正前後各次副歌變速後第二拍的相對時間](../../g11-storage-clock-follow/docs/images/midi-clock-chorus-tempo-step.png)

舊版長時間平均對變速反應慢，微小的速度修正還會延後下一次更新。修正版在連續四段 Clock 間隔一致指向明顯變速時，以變速起點重建速度估計，並讓尚未輸出的拍點使用新速度。測試同時檢查變速前小節起點不被改寫。理想輸入的回歸要求誤差不超過新速度的一個 Clock，實體數位回錄另外量測。

[各遍數據與檢查結果](tempo-step-summary.json) · [修正前回歸失敗](../band-overnight-20261122/step-red.log) · [完整測試紀錄](../band-overnight-20261122/full-final.log) · [八小時模擬](../band-overnight-20261122/eight-final.log) · [Clippy](../band-overnight-20261122/clippy-final.log)

修正已推回 [#1669](https://github.com/storytold/soundcraft/pull/1669)，維持草稿。[提交 d1545d2 的硬體報告與對照圖](https://github.com/mtlcl410/soundcraft/blob/d1545d2c00b80d0cde746d8d37b53e524175f5b5/docs/model-12-clock-follow-hardware.md#changing-tempo-at-the-chorus)。本機播放與 UI 函式庫分別 222、409 項通過，預設略過 5 項，其中八小時 Clock 抖動模擬另跑通過。格式檢查及兩個 crate 的 all-targets Clippy 完成，engine 既有 unused_mut 警告仍在。更新 PR 說明時，GitHub 尚未列出新提交的檢查結果。

## 測試範圍

伴奏只送到 Windows S/PDIF 數位回錄，這輪沒有量 Model 12 MAIN、錄人聲到 SD、人工聽辨或由演奏者彈 PC1X。Model 12 作為實體 MIDI 輸出介面；時鐘與時間碼由電腦產生。先前使用 Model 12 面板發碼與 MAIN 的紀錄另見[實機副歌驗收](../band-chorus-live-20261122/REPORT.zh-TW.md)。
