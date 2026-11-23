# G-11 三支草稿 PR 的提交清點

GitHub 已核對三支 PR 的 head、草稿狀態與說明。每支各有一個整理提交；上層另用 merge 承接下一層。沒有執行新測試或修改產品行為。說明中的數字沿用既有驗證，保留其適用版本與限制。

| PR | 本層比較基準 | 檔案數（前 → 後） | GitHub 說明字元數（前 → 後） | 最新 head | 本層逐檔用途與分類 |
| --- | --- | ---: | ---: | --- | --- |
| [#1662](https://github.com/storytold/soundcraft/pull/1662) | main | 34 → 33 | 18,830 → 3,449 | `168a1810` | [Beat Clock 輸出](audit1662.md) |
| [#1663](https://github.com/storytold/soundcraft/pull/1663) | #1662 | 44 → 44 | 30,282 → 3,554 | `14030820` | [MTC 產生與追隨](audit1663.md) |
| [#1669](https://github.com/storytold/soundcraft/pull/1669) | #1663 | 93 → 78 | 23,640 → 4,427 | `c093aedb` | [外部 Beat Clock 跟隨](audit1669.md) |

檔案數按每層與其基準的三點差異計算；說明長度按 GitHub API 傳回的正文計算。合併順序為 #1662 → #1663 → #1669。共享路線圖和差距文件各自只說明本層功能。

## 移出及保留的內容

- #1662 移出 `crates/playback/src/sync_timing_test.rs` 的單次主機計時探針；同檔的 MIDI 虛擬迴路驗證已搬到 `sync_output_tests.rs`，保留斷言及手動執行方式。
- #1663 移出只量單機 quarter-frame 間距的探針。保留具斷言的長時間幀率測試並標為 ignored。
- #1669 用一般刪除提交移出 `docs/model-12-clock-follow-hardware.md`、`docs/external-clock-response-measurements.md`、十張 `midi-clock-*.png` 和一張 `model-12-main-loop-clock-follow.png`。移出只列印時間的 snapshot 探針。`ATTRIBUTION.md` 回復為下層內容，下層已移出的測試檔也不再占此層差異。八小時抖動、十分鐘封包群聚及 96 相位波形掃描保留為 ignored 回歸測試，PR 說明附指令。
- [#1669 的單一證據留言](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268) 收錄兩份報告和全部 11 張內嵌圖片。[#1661 的留言](https://github.com/storytold/soundcraft/issues/1661#issuecomment-7072496821) 連到同一份。圖源固定在刪除前的提交；已逐張比對雜湊並核對 GitHub 顯示的圖片數。`docs/midi-input.md` 的外部 Clock 硬體註記只留 Model 12 經 UM-ONE 已驗證、Akai MPC 未實測的聲明。
- 沒有提交量測腳本、log、CSV 或暫存檔。本輪核對了逐層 diff、git diff --check、合併父提交、GitHub 正文與遠端 head；未重新量測音訊或執行 CI 指令。

## Cargo 相依

- #1662 以 `craft-midi-sync` 名稱引用 `craft-midi@08da5e14` 的同步訊息編碼，既有使用端繼續用 `45a8e166`。Playback 加入 `thread-priority 3.1.1` 供 MIDI 輸出執行緒盡可能提高排程優先度。鎖檔的來源標示與沿用的間接相依列在 [#1662 清單](audit1662.md)。
- #1663 沒有 Cargo 相依變更。
- #1669 為既有 playback crate 增加選用的 `test-input` feature，UI 的開發相依啟用它，以便無硬體驗證音訊與 MIDI 錄音。沒有新增外部套件或鎖檔項目。

## Open questions

### #1662　Beat Clock 輸出

1. 能驗證實際播放時序和安全重開流程後，自動恢復是否也要支援獨占式音訊後端？
2. 停止中定位要立即送 Song Position Pointer（SPP），還是等下次從非零位置起播才送？
3. 輸出時間戳中斷後，在一個四分音符內均勻補齊所有欠下的 F8，是否適合靠計數定位的裝置？MIDI 規格與 Pro Tools 手冊均未指定此情況。
4. 同名 MIDI 埠如何分別保存校準值？
5. 是否保留 ±250 ms 的補償上限？
6. 沒有輸出目的地時是否顯示時序警告？
7. 外部 MIDI 軌輸出可用前，是否顯示 Notes/Controllers 補償偏好？
8. 演奏中外掛延遲改變，是否需要不同的重新對齊方式？
9. 密集速度圖每 1,000 次定位耗時 0.337 ms，是否需要進一步改善？
10. 同步偏好有單一欄位損毀時，是否只重設該欄位？

### #1663　MTC

1. 收到 full-frame 定位時，是否與 Session Setup 採相同的分數取樣捨入規則？
2. 解碼前是否剔除交錯在 MIDI 原始資料中的即時訊息位元組？
3. 佇列中的 Online Record 遭拒時，是否顯示與手動指令相同的原因？
4. 時間碼跨午夜時，走帶是否繼續進入下一天？
5. 啟用 Automation Follows Edit 時，Keep Clips at Their Timecode 是否同步移動自動化？
6. 專案中的同步欄位損毀時，是否逐欄復原？

### #1669　外部 Beat Clock 跟隨

1. Coast 仍在播放時，僅恢復 F8 就重新鎖定速度和相位，是否符合預期？
2. 跟隨反應要固定或讓使用者調整？±8% 連續推速的峰值是 3.8333 ms。[Bitwig 的同步反應滑桿](https://www.bitwig.com/userguide/latest/the_dashboard/)
3. 大緩衝且時脈穩定時，是否接受預測到裝置實際交付期限？20% 減速矩陣中，第一下反拍為 −25.000 至 +86.500 ms，下一拍為 −25.000 至 +83.771 ms。已交付的聲音無法改期，最晚值發生在恢復一個 pulse 硬上限之後。
4. 外部定位期間，是否繼續停用本機循環？
5. 播放中收到 SPP，是否繼續忽略？
6. Stop 除了重設外掛，是否也逐音送出 Note Off？
7. 長時間演出要保留多少速度歷史？
8. 外部跟隨偏好損毀時，是否逐欄復原？
