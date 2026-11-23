# #1669 外部 Beat Clock 跟隨驗收

本輪使用可重放的 F8 時戳，逐塊驅動 SoundCraft、Sampler 與節拍器，再從實際 48 kHz PCM 找起音與最後一個非零取樣。正值表示晚於來源樂譜。裝置提前量與緩衝採可控制的模擬值，這次沒有重新量 Model 12 的實體 MAIN。原始逐音資料保留取樣精度，表內單位為毫秒。

## 大幅變速與封包到達時間

12 種速度與切點各跑三種輸入，合計 36 組、1,782 個八分音符，每個只有一個完整的 96 取樣波形。下表每格依序列出變速後第一個八分音符的帶號偏差、第二拍起的最大絕對偏差，以及確認變速時經過的 F8 數。第 384 個 F8 位於小節線，第 396 個位於拍中。封包群依序含 3、4、5 個 F8，各群第一個 F8 按樂譜抵達，其餘在 1 ms 內送出。

{{PACKETS}}

±1／±2 ms 的兩種輸入都在 8/12 組用兩個間隔確認，其餘在第 3 或第 4 個 F8 完成四間隔判定。36 組皆只有一次確認，變速前及變速後額外誤觸皆為 0。集中到達時，兩個獨立群組間隔實際經過 7 個 F8，四個間隔則經過 15 個。180→60 時第一下早 196.896 ms。±1 和 ±2 ms 抖動的第二拍起峰值分別為 4.750 和 4.188 ms；加入抖動後有 3 組超過 4 ms。抖動回歸門檻是第一下 10 ms、後續 6 ms；理想時脈維持 10／4 ms。舊版成批測試出現 194 次斷鐘判定及 88 個空拍位／88 個擠入多個起音的拍位。估速改按封包群的時間與跨越的 pulse 數計算，保留每個 F8 的音樂位置。[修正前紀錄](packet-data/red.log) · [整合版每個八分音符](packet-data/integrated-eighths.csv) · [確認時間與尾音檢查](packet-data/integrated-summary.csv)

穩速 120 BPM 以固定 3、4、5，以及循環 3／4／5 成群各跑 10 分鐘。每輪 2,400 個音的起音偏差均為 0，尾音完整。從起播計，大幅變速誤觸、斷鐘、漏音與重複都是 0。[包含起播的逐音紀錄](packet-data/integrated.log)

## 高 BPM 的裝置交付與減速

兩種策略在相同輸入上比較。硬上限最多排到最後 F8 加一個 pulse。新策略只在已鎖定、輸入規律，而且整個裝置緩衝至少一個 pulse 時，才排到該音訊區段實際要交付的位置。遇到變慢、下個 F8 逾期、封包集中或確認推速時恢復硬上限；若之後真正斷鐘，仍依 Coast 或 Stop on loss 設定處理。

穩速每格、每個策略渲染 32 個音與 16 個節拍器聲，各自比對完整參考波形。8 格短緩衝兩種策略的整段 PCM 逐取樣相同，起音延遲 +20.646～+58.646 ms。10 格可預測的設定從硬上限的 +28.646～+85.104 ms 改善為 0 個取樣誤差。每個策略合計 864 聲均無漏音、重複或截尾。[穩速個別起音與尾端](lead-data/device-lead-steady-onsets.csv) · [舊版失敗](lead-data/red.log)

減速取原速的 80%（200→160、240→192、300→240），每格遍歷 24 個 pulse 位置與 4 種 callback 對齊，共 96 種。Offbeat 是嚴格晚於切點的第一下反拍，Beat 是下一個四分音符拍點。兩欄都是 96 組裡絕對值最大的帶號誤差，含單獨渲染的節拍器比對。若把切點正好落在整拍的那一音也算入，該拍的硬上限誤差為 +20.646～+82.875 ms，新策略為 0～+57.979 ms。每個帽鈸的力度不同，用以辨認個別音，避免把晚到超過半個八分音符的音算成下一個音。每格包含 11 個帽鈸與 6 個節拍器聲。

{{DEVICE}}

{{DEVICE_ZH}}

[硬上限逐音](post-slow-hard.csv) · [有條件預測逐音](post-slow-predict.csv) · [減速矩陣](slowdown-summary.csv) · [提前交付時機](slowdown-predict-commit-window.csv) · [舊版完整紅測](ramp-data/sweep-red.log) · [交接修正前逐格失敗數](handoff-red-summary.csv) · [修正後公開回歸的兩種策略](release-sweep.log)

## 連續推速與抗抖動

±8% 推速從 124 BPM 起，32 小節逐步加速或減速，再用 32 小節回到原速。舊版最早的一個八分音符為 −435 samples（−9.0625 ms），估速落後與網格相位的修正速度共同造成該偏差。採用偵測長窗曲率、只加快持續推速時的相位修正後，升速在乾淨／±1／±2 ms 的峰值為 2.3542／2.4375／3.8333 ms，降速為 2.7708／2.9167／3.7500 ms。6 輪各 513 個音，全數波形完整。124.0→124.3→124.0 的三輪各有 257 個音，持續推速與大幅變速皆 0 次誤觸。顯示數值統計從輸入已鎖定且經過一拍起算，連續估值變化最大 0.09139 BPM。[舊版紅測](ramp-data/red-production.log) · [整合後測量](ramp-data/integrated.log) · [各候選方案、每個八分音符及尾音](ramp-data/ramp-eighths.csv) · [候選方案比較](ramp-data/REPORT.zh-TW.md)

八小時 ±0.2 BPM 網格驗證前後峰值皆為 148 個取樣；另外把八小時實際逐段渲染，115,201 個起音的峰值為 234 個取樣（4.875 ms），前後逐音 CSV 的 SHA-256 完全相同，每個尾音 96 個取樣。九組穩速 BPM／相位 p95 原值維持，12 組理想變速的每一音另與原紀錄比對。128↔140 的 16 組控制通過，Coast 只恢復 F8 後仍有 65/65 聲，Stop on loss 保持停止。[八小時 PCM 修正前](flutter-before.csv) · [修正後](post-flutter-final.csv) · [既有八小時網格](post-eight_hours_of_clock_flutter-final.log) · [理想輸入](ideal-all.log) · [128↔140](post-scenario_a2_drop-final.log) · [Coast](post-returning_clock_without-final.log)

## 驗證與複查

{{TESTS_ZH}}

Avid 說明送出 Beat Clock 與測量固定偏移的方法，文件印刷頁碼為 743–744。Bitwig 的 Synchronization Settings 提供調整速度跟隨反應的滑桿。#1669 的 Open questions 保留交由音樂人決定的問題，包括反應應固定或可調，以及大緩衝減速的可接受程度。[Avid Pro Tools Reference Guide 2026.4](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf#page=845) · [Bitwig Studio User Guide](https://www.bitwig.com/userguide/latest/the_dashboard/)
