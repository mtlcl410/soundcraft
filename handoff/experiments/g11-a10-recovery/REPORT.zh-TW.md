# A-10　輸出時間戳恢復後的 Beat Clock 與 MTC

2026-11-22，Windows。本輪量測補償輸出從 unknown 恢復，在相同播放段繼續走帶時，模擬 MIDI 接收端實際收到的封包。音訊回呼每 10 ms 發布一次、輸出埠每 1 ms 輪詢，48 kHz、120 BPM、MTC 25 fps。對照使用同一條播放時間線，只有有效輸出時間戳的缺口不同。沒有操作 Model 12 或量實體 USB 延遲。

## 歸屬及紅測

| 版本 | 同一項 Clock 回歸 | 同一項 MTC 回歸 |
|---|---|---|
| upstream main `85623f28` | 無 Beat Clock 輸出、共用排程器或對應測試入口 | 無 MTC 輸出；測試篩選共匹配 0 項。[執行紀錄](main-requested-red.log) |
| #1662 `91366d09` | 失敗。首個 F8 到期於 104.167 ms，200 ms 才交付；其後連續四個間隔均為 1 ms。[原版紅測](beat-requested-red.log) | 這支 PR 還沒有 MTC encoder |
| #1663 `0819e610` | 相同失敗，繼承自 #1662 | 失敗。100 ms 缺口後首個 QF 晚 100 ms；30 ms 的短缺口也送出逾期訊息。[修正前兩項失敗](mtc-requested-red.log) · [100 ms 逐筆交付](mtc-before.log) |
| #1669 `82cc19c6` | 原 A-10 同樣重現 | 原 A-10 同樣重現。[整合版修正前](follow-before.log) |

Clock 回歸為 `recovered_clock_repays_missing_ticks_evenly_within_one_beat`，MTC 回歸為 `recovered_mtc_locates_live_and_starts_a_complete_quarter_frame_group`。兩者從排程器向模擬埠交付時取樣，分別比較排定時間及實際交付時間。舊 A-10 同時要求每個 F8 都對齊原 24 PPQN 網格；在一拍內平均補回遺漏 tick 的新規格下，補回期間的中間 tick 有自己的期限，首個和補完後的 F8 才使用正常網格。

## Beat Clock 的交付紀錄

100–200 ms 間沒有有效時間戳，補償輸出保持安靜。舊版及修正版最後都是 49 下，計數包含 0 與 1000 ms 兩端。舊版的缺陷是 5 個逾期 tick 集中送出。修正版保留已欠的 5 下，從下一個有效格點開始平均補回，外接裝置可以持續數 tick，恢復期間沒有額外的 Stop、SPP、Start 或 Continue。

| 項目 | 修正版模擬埠 |
|---|---|
| 第一個恢復的 F8 | 正常格點 208.333333 ms，209 ms 實際交付，晚 **0.666667 ms** |
| 補回區間 | 209–688 ms，共 29 個 F8、28 個間隔。排定間隔約 17.113 ms |
| 全部 28 個實際間隔，依發送順序，ms | 17, 17, 17, 17, 17, 18, 17, 17, 17, 17, 17, 17, 17, 17, 18, 17, 17, 17, 17, 17, 17, 17, 17, 18, 17, 17, 17, 17 |
| 回到正常速度 | 一拍期限 700 ms；屆時累計與對照相同，其後實際交付與無中斷對照逐筆一致。正常排定間隔 20.833 ms |
| 另測 50–250 ms 的 200 ms 缺口 | 第一個 F8 到期並交付於 250 ms。33 個 F8、32 個間隔，各 15 ms。全程 49/49；一拍後逐筆匹配 |
| 其他狀態 | 補回中按 Stop 會結束補回，新 transport pass 正常 Start；兩次輪詢之間已失效又恢復時，僅取消受影響補償路由上的舊期限，未補償路由繼續交付 |

[Clock 逐次實際間隔及完整套件](beat-paced-suite-final.log)

## MTC 的定位和重新起送

100–200 ms 缺口後，200 ms 先送一個 full-frame，定位到 00:00:00:05。略過 14 個無法接成新群組的 QF，第一個新群組從 240 ms 的 piece 0 開始，排定與交付相差 **0 ms**。piece 0–7 的交付時間依序為 240、250、260、270、280、290、300、310 ms。恢復到第一個 QF 的 40 ms 是等待下一個完整群組起點。另測 20–50 ms 缺口，50 ms 定位到第 1 格，80 ms 起連續發送新群組。[MTC 逐項紀錄](mtc-paced-suite-final.log)

## 整合與驗證

[Clock #1662](https://github.com/storytold/soundcraft/pull/1662) `b1a9d50c` → [MTC #1663](https://github.com/storytold/soundcraft/pull/1663)（merge `17d5f03`，MTC 修正 `7e6215a2`）→ [整合 #1669](https://github.com/storytold/soundcraft/pull/1669)（merge `49a85d8e`）。三支都維持草稿。

三支修正版的 `cargo test -p soundcraft-playback -- --nocapture --test-threads=1` 分別通過 154、191、227 項；各略過 2、3、4 項。三支的 `cargo fmt --all -- --check` 與 `cargo clippy -p soundcraft-playback --all-targets -- -D warnings` 均通過。[#1669 整合套件](follow-paced-suite-final.log) · [#1662 Clippy](beat-paced-clippy.log) · [#1663 Clippy](mtc-paced-clippy.log) · [#1669 Clippy](follow-paced-clippy.log)

擴大到 engine 的既有嚴格 Clippy 檢查仍有 `crates/engine/src/autosave.rs:481` 的 `unused_mut`；main 與 #1669 的檔案物件同為 `82def8be`，本次未修改該檔。[先前嚴格檢查原始紀錄](../g11-coast-verification/clippy-final.log)

#1662 的 Open questions 留待使用者確認「一拍內平均補回」的硬體適用性。MIDI 規格與 Pro Tools 手冊未指定音訊裝置時間戳失效後要如何恢復。#1669 的 Open questions 另請使用者確認 `82cc19c` 的輸入行為：已在 Coast 播放時，回來的 F8 足以重新估速後即恢復跟隨；Stop on loss 仍須等外部走帶命令。[MIDI Timing Clock](https://midi.org/summary-of-midi-1-0-messages) · [Pro Tools Reference Guide](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2020.12.pdf)
