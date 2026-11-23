# MTC 情境驗收

執行版本為 #1663 的 `0819e6101d115e9bc2f1e61e2cfac66c9a2731f1`。軟體控制台把 MIDI payload 交給正式 reader，把可預測的時鐘交給播放回呼與輸出編碼器。在要求量測聲音的項目，C-4 從輸出 PCM 掃描節拍起音，B-4 從兩個實際寫完的 WAV 驗證已錄到的取樣位置。模擬可隔離裝置驅動、USB 傳輸及回錄延遲。

## E　輸入資料

| ID | PR、head | 結果 | 測量與重現方式 |
|---|---|---|---|
| E-1 | #1663 `0819e610` | 失敗，#1663 的 MTC reader | F8、FA、FC 個別插在 full-frame SysEx 內及 F1 與資料位元組之間，6 種輸入全部失去 MTC 訊息。`scenario_e1_interleaved_wire_realtime` 保留為紅測。這量到傳入 reader 的原始 payload，透過作業系統先拆開即時訊息的裝置可能有不同結果。 |
| E-2 | #1663 `0819e610` | 通過 | 9 種畸形 SysEx，以及各重複三次的缺件、亂序、逆向 quarter-frame 群組均未移動 transport。`scenario_e2_reject_invalid_timecode`。 |
| E-5 | #1663 `0819e610` | 通過 | 固定種子的 10,000,000 bytes，分 1,554,172 個 1～12 byte payload，363 次有可取出的事件。固定大小的 1,040-byte reader 使用定長儲存，測試完成。`scenario_e5_ten_million_reader_bytes`。 |

原始紀錄見 [mtc-e.log](mtc-e.log)。Windows 可從 [獨立工作樹](mtc-tree) 用下列命令重跑。以一般已配置 Rust 的環境執行時，可將批次檔換成 `cargo`。

```powershell
& E:/soundcraft/tmp/1663-storage-mtc-build.cmd test -p soundcraft-playback --lib mtc::tests::scenarios -- --nocapture --test-threads=1
& E:/soundcraft/tmp/1663-storage-mtc-build.cmd test -p soundcraft-playback --lib scenario_a10_d4 -- --nocapture
& E:/soundcraft/tmp/1663-storage-mtc-build.cmd test -p soundcraft-playback --lib scenario_c4_two_hour_drift_render -- --ignored --nocapture --test-threads=1
& E:/soundcraft/tmp/1663-storage-mtc-build.cmd test -p soundcraft-engine --lib scenario_d3 -- --nocapture
& E:/soundcraft/tmp/1663-storage-mtc-build.cmd test -p soundcraft-ui-egui --lib scenario_b5 -- --nocapture
& E:/soundcraft/tmp/1663-storage-mtc-build.cmd test -p soundcraft-ui-egui --lib scenario_d4_transport -- --nocapture
```

## A　DJ 演出

| ID | PR、head | 結果 | 量測與測試 |
|---|---|---|---|
| A-9 | #1663 `0819e610` | 通過 | 播放中往返 20 個 cue（10～20 秒），20 個 full-frame 定位與 790 個依序正確的 quarter-frame，穩定階段無額外 full-frame、無逆向 QF。接收器最慢 190 ms 上鎖。`scenario_a9_b2_generator_restarts`。[逐輪重新定位](mtc-restarts.log) |
| A-10 | #1662/#1663，整合於 `0819e610` | 200 ms 失去輸出時間戳的案例通過，100 ms 案例有逾期交付 | 同一 transport pass。250 ms 起原 stream 失去有效報告而保留舊值，300 ms 換新的 StreamLead，警告變為 Unknown；500 ms 恢復有效值並清除警告。這 200 ms 內補償輸出等待。恢復後補發在等待期已到期的 F8／F1 各 **0** 個。首個 F8 的排定與交付均為 500.000 ms，MTC 等完整群組於 540.000 ms 恢復。恢復後第 100 ms 起 F8、QF 對格線的最大交付誤差分別為 0.833、0 ms。相同 reset 對 48,000 個雙聲道 PCM frame 與對照逐取樣相同。另一輪 100 ms 的失效期則含恢復瞬間有 F8、F1 實交晚 95.833、100 ms；兩輪不同長度會走到不同的趕發／丟棄條件。完整的初始交付及警告時點見 `scenario_a10_d4_two_encoders_and_stream_reset`、`scenario_a10_render_continues_across_stream_reset` 和主報告的短中斷重現。[200 ms 交付紀錄](mtc-a10d4-final.log) · [100 ms 交付紀錄](a10-final.log) · [PCM](mtc-short.log) |

## B　樂團演唱會

| ID | PR、head | 結果 | 量測與測試 |
|---|---|---|---|
| B-2 | #1663 `0819e610` | 通過 | 25 fps，播放 8 小節後倒回 8 小節，重做 30 次，共 30 個停於新 cue 的 full-frame，另有 30 個重新起播 full-frame、48,000 個 QF。每次上鎖均在 150 ms 內，低於 8 格的 320 ms。每次連續播放內位置皆前進。`scenario_a9_b2_generator_restarts`。[逐輪重新定位](mtc-restarts.log) |
| B-3 | #1663 `0819e610` | 通過，含失碼偵測視窗 | 25 fps、最後一個 QF 後，None 在 80 ms（兩格）確認失碼並停止。4／8／40 frames 分別在 160／320／1,600 ms 停止，Jam Sync 持續 10 秒，模擬播放裝置無漂移時差 0 samples。[Pro Tools Reference Guide 2026.4，第 1819 頁](../../tmp/Pro_Tools_Reference_Guide_2026.4.pdf#page=1921)列出 None、4～40 格（預設 8）及 Jam Sync；None 的兩格失碼門檻見本分支文件。`scenario_b3_loss_modes`。[短測](mtc-short.log) · [SoundCraft 行為說明](mtc-tree/docs/midi-input.md) |
| B-4 | #1663 `0819e610` | 通過 | Generator ON、Online OFF 時從主機錄音指令進入 recording。播放 250 ms 時切入錄音，測試回呼及正式寫檔器產生兩個單聲道 WAV。三個參考點比對兩軌共 6 個起音，套用錄音起點後全部 0 sample 偏差；各軌實際起音是 24,013／48,013／84,013 與 24,064／48,064／84,064 samples。連續 200 個 QF 間隔均 10.000 ms，起播僅一個 FF。主機條件及音訊寫檔分層驗證。`scenario_b4_generator_accepts_host_record`、`scenario_b4_record_while_generating`。[主機錄音](mtc-b4-host.log) · [WAV／MTC](mtc-short.log) |
| B-5 | #1663 `0819e610` | 失敗，#1663 的 queued Record 無可見說明 | 在 egui 軟體介面點真實走帶錄音鍵或送 F12，兩者都顯示「Take MTC chase offline before recording」。排入同一主機 transport queue 的 Record 被移除，狀態列為空字串。三者都保持 Online、未進入錄音，暫存錄音目錄均為 0 檔。`scenario_b5_three_online_record_requests`。[紅測](mtc-b5-verified.log) |

## C　管絃與長時間同步

| ID | PR、head | 結果 | 量測與測試 |
|---|---|---|---|
| C-1／C-8 | #1663 `0819e610` | 失敗，#1663 的整格定位 | 六種幀率各 600 秒、每種量 44.1／48／96／192 kHz。六種滾動 QF 的取樣位置均與獨立四分格換算完全相符，0 次誤報，改為不符的整數幀率後每組都產生警告。停止中 full-frame 定位有 **67,793 次早 1 sample**，例如 23.976 fps × 44.1 kHz 的第 1 格得到 1,839，Session Setup 為 1,840。Reader 的 `Position::samples` 取最近樣本，Session Setup 的 `FrameRate::samples_at_frame` 取第一個屬於該格的樣本。以下表列每種組合的失配數。`scenario_c1_c8_ten_minutes_six_rates`。[紅測及所有幀率數字](mtc-short.log) |
| C-2 | #1663 `0819e610` | 通過 | 29.97 DF 的 00:00:59:29→00:01:00:02 與 00:09:59:29→00:10:00:00 的線上標籤及樣本位置均正確連續，48 kHz 兩對相差 1,602、1,601 samples。跨邊界 4 個已鎖群組位置皆遞增。`scenario_c2_c3_midnight_and_df`。[短測](mtc-short.log) |
| C-3 | #1663 `0819e610` | 小時通過；午夜產品行為待定 | 30 fps、48 kHz。00:59:59:29→01:00:00:00 相差 +1,600 samples。午夜接收連續 QF 保持鎖定，線上位置 4,147,199,600→2,800 samples，隨時間碼回到新的一天。錄音師希望跨日延續同一個專案日，目前仍屬產品決策。`scenario_c2_c3_midnight_and_df`。[短測](mtc-short.log) |
| C-4 | #1663 `0819e610` | 通過已記載的重新定位行為 | 真實 PCM 回呼各模擬兩小時，30 fps 音源、48 kHz 裝置時脈 −50／+50 ppm。兩輪都只取得一次鎖、0 次失鎖，掃描起音沒有重複或缺拍。最大起音偏差分別為 **33.414／33.373 ms**；最後一拍 +26.039／−26.020 ms。每輪 10 次 hard relocate，分別每次 +1,603／−1,603 samples（33.396 ms）。這符合目前「持續一秒超過一格才重新定位」的設計。相較共用音訊時鐘，長演出可觀察到整格修正。`scenario_c4_two_hour_drift_render`。[四小時 PCM、每次 relocate 時間](mtc-long-final.log) · [行為說明](mtc-tree/docs/midi-input.md) |

### C-1／C-8 每種取樣率早一個取樣的次數

| Session fps | MTC wire rate bits | 定位標籤數 | 44.1 kHz | 48 kHz | 96 kHz | 192 kHz |
|---|---|---:|---:|---:|---:|---:|
| 23.976 | 24 | 14,385 | 7,015 | 0 | 0 | 0 |
| 24 | 24 | 14,400 | 0 | 0 | 0 | 0 |
| 25 | 25 | 15,000 | 0 | 0 | 0 | 0 |
| 29.97 ND | 30 | 17,982 | 8,811 | 7,192 | 7,193 | 7,193 |
| 29.97 DF | 29.97 DF | 17,982 | 8,811 | 7,192 | 7,193 | 7,193 |
| 30 | 30 | 18,000 | 0 | 0 | 0 | 0 |

相同 C-1 測試再跑 #1669 `6b82d9bc84af17b259b98970dc5557a93c80d7a0`，六種幀率、四種取樣率的 390,996 個整格結果均精確，誤差共 **0 次**。該分支的 `bfecc6e` 已讓整格沿用 Session Setup 的換算。下一輪只需將這項既有修正帶回較低的 #1663，保持兩個 PR 自身可驗證。[同測試整合版紀錄](mtc-c1-integrated.log)

MTC 有四種線上 rate bits。23.976 與 29.97 ND 依專案速率解讀與其配對的 24、30 標籤。QF 的傳送間隔依各自實際有理數 fps 產生。

## D　錄音室

| ID | PR、head | 結果 | 量測與測試 |
|---|---|---|---|
| D-3 | #1663 `0819e610` | Undo／Redo 通過；automation 行為待決策 | 在 48 kHz 專案將 Session Start 從 01:00:00:00 移到 00:30:00:00，選 Keep clips at their timecode。13 個 clips 均後移 86,400,000 samples。開／關 Automation Follows Edit 時，兩輪的 automation 點（第 50,000 個 sample）、所有 markers 與 tempo map 均保持原位，undo 還原、redo 重套後都與快照完全相符。`scenario_d3_session_start_undo_redo`。[完整快照比較](mtc-d3.log) |
| D-4 | #1662/#1663，整合於 `0819e610` | 通過 | 48 kHz、選取 48,000..96,000 samples，加前滾 24,000／後滾 12,000。實際主機 transport 的 from/end 為 24,000／108,000。兩個產生器的共同埠送出 500 ms 的 SPP=4 及 25 fps、frame 12 的 full-frame；第一個 QF 經過其後，stop 在 start 後 1,750 ms。相鄰兩個獨立層驗證。`scenario_d4_transport_pre_and_post`、`scenario_a10_d4_two_encoders_and_stream_reset`。[主機起訖](mtc-d4-host.log) · [MIDI 訊息順序](mtc-a10d4-final.log) |
| D-5 補充 | #1663 `0819e610` | MTC 專案既有設定遷移通過 | 舊 `midi.mtc.external_offset_frames=+100` 移到 `sync.external_offset=+160000` samples；若已有不同的 +42 samples 則保留衝突並提示，重開保留兩個值。這驗證 MTC 的正號保留。另有 #1669 Clock follow 的 legacy input sign inversion，見主報告 D-5。`existing_offset_and_freewheel_preferences_migrate_once_and_conflicts_survive`。[重跑紀錄](mtc-d5.log) |
