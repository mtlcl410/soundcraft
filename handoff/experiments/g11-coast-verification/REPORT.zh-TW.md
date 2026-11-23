# #1669　DJ 主鐘中斷後僅恢復 F8

2026-11-22。本案延續先前 A-3 的軟體驗收。[原始 38 項情境報告](../g11-scenarios-20261122/REPORT.zh-TW.md)

## 歸屬與修正

上游 main `85623f28` 沒有 `setup.midi_clock_follow` 命令、Coast 狀態或對應的跟隨器。#1662 和 #1663 的受測 head 同樣沒有這兩個模組。此行為由 #1669 引入；可以重現的修正前版本是 `6b82d9bc`。[版本核對](ownership.log)

失鐘時，跟隨器清除速度估計並保留當時的脈衝週期。舊版只有收到 Start 或 Continue 才允許回到 Locked，所以即使新脈衝已量出 128 BPM，播放網格仍照先前速度走。修正後，Coast 中收到連續且能算出有效速度的 F8，便將回來的脈衝對應到延續播放網格上最近的位置，讓後續編曲跟隨新的速度及相位。重新鎖定不發起第二次 Play 或 Locate。Stop on loss 和明確 MIDI Stop 仍須由外部走帶命令起播。F8 本身沒有歌曲位置，故這種重鎖不能辨識刻意換到另一個小節。

## 相同伴奏的前後結果

48 kHz，120 BPM 起播，從第 8 秒起省略 14 個脈衝；替代來源在 8.300 秒開始送 128 BPM 的 F8，包含相位位移。以正式 MIDI reader 和可編輯拍點網格驅動內建 sampler 及 mixer，在實際渲染的 PCM 上數八分音符的起音。正號表示比獨立主鐘的參考拍晚。

| 策略 | 舊版 | 修正版 |
|---|---|---|
| Coast | 最終仍為 Coasting；65/65 下，最後一音晚 22,725 samples（473.438 ms） | 最終 Locked，估速 128.000 BPM；65/65 下，無遺漏或重複，最後一音晚 118 samples（2.458 ms），在 4 ms 目標內 |
| Stop on loss | 約 8.137 秒停，33 下；F8 恢復後仍為 Stopped | 相同停止位置（第 390,563 個取樣）、33 下，後續 F8 沒有重新啟動 |

原 A-3 的 [修正前紅測](before.log) 與 [修正後重跑](after-original.log) 使用同一個測試檔。另加入可放進 CI 的 PCM 測試，核對全部起音的數量和對應位置、末音誤差、最終 BPM，以及 F8 恢復時沒有走帶命令。這輪的音訊量測來自離線渲染，未加入音訊介面或 USB 的往返延遲。

第一個恢復後的踩鈸早 200 samples（4.167 ms），其後各起音的最大絕對偏差為 185 samples（3.854 ms）。全段的峰值是 750 samples（15.625 ms），包括還沒有新脈衝可參考的中斷區間。末音比對的是第 65 個獨立起音。[逐項 PCM 斷言](final-pcm.log)
## 版本與本機驗證

修正提交 [82cc19c](https://github.com/storytold/soundcraft/commit/82cc19c)，推回 [#1669](https://github.com/storytold/soundcraft/pull/1669)。原測試用來比較紅／綠兩個版本；PR 中的正式回歸測試可獨立重跑。

~~~text
cargo test -p soundcraft-ui-egui --lib returning_clock_without_continue -- --nocapture
cargo test -p soundcraft-playback -p soundcraft-ui-egui
cargo fmt --all -- --check
cargo clippy -p soundcraft-playback -p soundcraft-ui-egui --all-targets
~~~

兩個 crate 共 942 項通過，5 項標為 ignored；格式、all-targets Clippy 通過。[完整測試](full-final.log) · [正式回歸測試](committed-pcm.log) · [Clippy](clippy-checked.log)。額外用 `-D warnings` 時，Windows 在 `crates/engine/src/autosave.rs:481` 的既有 unused_mut 停下；main、修正前後三版的檔案物件 SHA 相同（`82def8be59`）。[嚴格模式紀錄](clippy-final.log)
