# G-11 樂團與錄音室情境驗收

2026-11-22，Windows。共 38 個指定案例，另加一首連續的 80 → 130 → 80 BPM 電子舞曲。每支 PR 都在其指定提交上驗證。所有聲音時序數字均取自 PCM 起音或錄完的 WAV；MIDI 發送另記預定送出和實際交付給模擬埠的兩個時間。模擬的軟體端交付、音訊期限和實體 USB 往返是三種不同的量測。

| 代號 | PR 及測試提交 | 詳細資料 |
|---|---|---|
| O | [#1662](https://github.com/storytold/soundcraft/pull/1662) `91366d09fd5f925492152c00be914d7dff7c0330` | [輸出量測](beat.md) · [本機測試補丁](local-tests-1662.patch) |
| T | [#1663](https://github.com/storytold/soundcraft/pull/1663) `0819e6101d115e9bc2f1e61e2cfac66c9a2731f1` | [MTC 量測](mtc.md) · [本機測試補丁](local-tests-1663.patch) |
| F | [#1669](https://github.com/storytold/soundcraft/pull/1669) `6b82d9bc84af17b259b98970dc5557a93c80d7a0` | [Clock 跟隨與電子舞曲](follow.md) · [本機測試補丁](local-tests-1669.patch) |

已在三支草稿 PR 的說明加入 Open questions，並將本輪數據發表於 [#1662 討論](https://github.com/storytold/soundcraft/pull/1662#issuecomment-7070842940)、[#1663 討論](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7070844245)、[#1669 討論](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7070845420)。本輪沒有推送程式或測試提交。

表中的「提議未達」代表附件提出的工作流程或數值目標，供 reviewer 決定。「觀察」記錄驗證到的產品行為，未把它計為規格違反。「紅測」指目前會失敗且已保留在本機的測試。若責任跨越 PR，表中分別標示。

## 第三項大幅變速複驗

[#1669 的修正 `af4af80b`](https://github.com/storytold/soundcraft/pull/1669/commits/af4af80b626bab785de97ba895f76187b76da99d) 已保留為草稿。原曲第一個減速反拍從**早 70.104 ms 改為 0.000 ms**，該段最大絕對偏差 0.167 ms。六種變速各測小節線與拍中，第一個反拍最大 1 sample，第二拍起最大 3 samples。向前、向後連續推速和穩速結果與舊版相同；A-1 連續 ±8% 的 4 ms 提議仍未達成。以下歷史資料保留原提交結果。[逐音數字、舊版失敗及抗抖動對照](../g11-large-tempo/REPORT.zh-TW.md)

## A-3 修正後複驗

#1669 已在同一首 48 kHz 伴奏上重測。失鐘 300 ms 後只送 F8，Coast 重新鎖到 128 BPM，65/65 下皆在。最後一音由晚 473.438 ms 改為晚 **2.458 ms**。恢復後首個踩鈸早 4.167 ms，其後剩餘起音最大絕對偏差 3.854 ms。Stop on loss 維持停止在第 390,563 個取樣，停前 33 下，隨後的 F8 沒有再次觸發播放。main 沒有外部 Beat Clock 跟隨器，修正歸屬 #1669。下列原始表格及優先順序保留修正前的量測。[前後對照與測試紀錄](../g11-coast-verification/REPORT.zh-TW.md)


## A-10 修正後複驗

upstream main 未提供這兩種輸出。Clock 的修正在 #1662（`b1a9d50c`），MTC 的修正在 #1663（`7e6215a2`），已依序 merge 到 #1669（`49a85d8e`）。100 ms 的缺口後，第一個 F8 晚 0.667 ms；5 個欠缺的 tick 於一拍內平均補回，全程 49/49。第一個 MTC full-frame 在 200 ms 定位到第 5 格，240 ms 起的 QF 依序準時交付。下方 A-10 表格保留原版紅測。[測量條件、每個 tick 的間隔、紅測與完整套件](../g11-a10-recovery/REPORT.zh-TW.md)

## A　DJ 與電子舞曲

| ID | PR / SHA | 判定 | 量測與歸屬 |
|---|---|---|---|
| A-1 | #1669 6b82d9bc | 提議未達 | 124→124.3→124 BPM 最大 3.792 ms；±8% 長推速最大 9.062 ms，理想無抖動也達 8.979 ms。9 組皆 0 次誤判 step。第一拍後顯示變化 ≤0.091 BPM，取得期最大 7.226。#1669 紅測 `scenario_a1_pitch_fader_rendered_hats`。 |
| A-2 | #1669 6b82d9bc | 通過 | 四種取樣率 × 兩個方向 × 拍頭／拍中，16 組。128↔140 BPM 首個八分音符 −4.312～+3.492 ms，其後最大 0.750 ms。[逐音帶號誤差](follow-ui-final.log) |
| A-3 | #1669 6b82d9bc | Coast 未重新鎖定 | 300 ms 斷鐘後只恢復 F8 並從 120 變 128。65 個音都在，末音晚 473.438 ms，狀態仍是 Coasting。Stop 策略約在 8.137 s 停下。#1669 紅測 `scenario_a3_resume_pulses_without_start`。 |
| A-4 | #1669 6b82d9bc | 通過 | 3、4、5 pulse 三種群聚各 10 分鐘、28,800 pulses。0 次掉鎖，取得期後 0 次假變速。穩定區讀值總範圍 119.9710～120.0484 BPM。 |
| A-5 | #1669 6b82d9bc / main | 起點通過；逐一 note-off 提議未達 | 50 Start 全部歸零、50 Continue 全部從 SPP；100 NoteOn 對 58 個明確 NoteOff，另 42 個由 plugin reset 釋音，0 個持續發聲。現有 main 也在 Stop 時 reset；外部硬體卡音未經證實。紅測 `scenario_a5_notes_released_across_random_stops`。 |
| A-6 | #1669 6b82d9bc | 六小時完成；記憶體上界待定 | 1,168,942 pulses、63 次變速。六個整時前的 PCM 起音 −1.667～+2.562 ms，沒有累積漂移趨勢；穩定區網格最大 4.688 ms。單次最多 2 個 transport 動作，tempo 歷史自第一小時 529 增至 2,703 筆（有效內容 43,248 B）。未量配置器總量或證明回呼零配置。[長測](follow-long-final.log) |
| A-7 | #1662 91366d09 | 通過 | 三個埠 −250、0、+250 ms，四種取樣率，最大實際交付誤差 0.494 ms；48 kHz 超額要求截在 ±12,000 samples。 |
| A-8 | #1662 91366d09 | 模擬通過 | A 埠在第八次 Clock 傳送失敗時回報斷線，B 繼續送出 63 個 F8。A 重開以 SPP 10、Continue、Clock 開始，首個 Clock 排定位置誤差 0 µs、實際交付晚 0.572 ms，後續最短實際間隔 20.506 ms。 |
| A-9 | #1663 0819e610 | 通過 | 20 次演出中跳 cue，20 個 full-frame、790 個順序正確的 quarter-frame。最慢 190 ms 重新鎖定。 |
| A-10 | #1662 91366d09 / #1663 0819e610 | 復原首批提議未達；穩定後通過 | 200 ms 未知後，0 筆過期交付，Clock 在恢復當下送出、MTC 在其後 40 ms 從新的群組起送。雙輸出重設，96,000 個 PCM 值和對照相同。250 ms 顯示保留延遲、300 ms 未知、500 ms 恢復；600 ms 起 Clock/MTC 交付最差 0.833/0 ms。在另一個 100 ms 未知區間，期間 0 筆，恢復當下 Clock/MTC 過期 95.833/100 ms；排定時間仍在格上。Clock 的游標與共用輸出在 #1662，MTC encoder 在 #1663。#1662 獨立紅測 `a10_first_clock_after_unknown_lead_is_handed_off_on_time` 也送出五個過期 F8（實交在 200、201、202、203、204 ms），確認 Clock 問題來自 #1662。整合紅測 `scenario_a10_dual_encoder_recovers_after_midroll_invalid_timestamp`。[#1662 單獨重現](beat-a10.log) [首批逐筆交付](a10-final.log) |
| 額外 EDM | #1669 6b82d9bc | 音數及尾音通過；時序提議未達 | 同一首 24 小節，每段 8 小節。192 個踩鈸、48 個底鼓、48 個小鼓皆在；尾音 96 samples 完整，之後一秒無多觸發。升速後踩鈸最大 17.896 ms，降速後 70.104 ms；末段最後的踩鈸、底鼓、小鼓分別晚 4.750、5.875、5.521 ms。#1669 紅測 `scenario_edm_eighty_one_thirty_eighty_rendered`。[逐段波形結果](follow-edm-24bars.log) |

## B　樂團與伴奏

| ID | PR / SHA | 判定 | 量測與歸屬 |
|---|---|---|---|
| B-1 | #1662 91366d09 | 播放通過；停止定位提議未達 | 12 首歌單，48 kHz 的 4,608 個 pulses 最大間隔誤差 0.1042 ms。11 個非零位置重新播放均送正確 SPP；停止中換到同樣位置 0/11 送出。#1662 紅測 `b1_stopped_setlist_locates_send_marker_spp`。 |
| B-2 | #1663 0819e610 | 通過 | 25 fps 倒回八小節再播 30 次，30 個 full-frame 後依序送出 48,000 個 quarter-frame，最慢 150 ms 重鎖，低於 8 frames 的 320 ms。 |
| B-3 | #1663 0819e610 | 通過；單列失碼偵測時間 | 25 fps，從最後收到的完整位置到停播，None / Frames 4 / 8 / 40 分別為 80 / 160 / 320 / 1,600 ms。None 的 80 ms 是辨識失碼的時間；Jam Sync 續播 10 秒，理想同速時差 0 sample。對照《Pro Tools Reference Guide 2026.4》印刷頁 1819 的 MTC、Frames、Jam Sync。[頁面摘錄位置](avid-page.txt) |
| B-4 | #1663 0819e610 | 通過 | 產生 MTC、Online 關閉，兩個實際 WAV 的 6 個錄音起音與預期各差 0 samples。開錄前後同一條傳送序列共 1 FF、200 QF，10 ms 間隔。 |
| B-5 | #1663 0819e610 | 拒錄與資料保護通過；提示失敗 | 面板、快捷鍵、已排隊的 Record 三路均未寫檔。排隊路徑留下空白狀態，未顯示原因。#1663 紅測 `scenario_b5_three_online_record_requests`。 |
| B-6 | #1669 6b82d9bc | 通過 | 100→120 BPM 跟鐘時同步錄音訊與 MIDI，關閉跟隨、存檔重開後分軌渲染。6 對起音的差全為 0 samples。[PCM](studio-deterministic.log) |
| B-7 | #1662 91366d09 | 通過 | 2,048 samples PDC，四種取樣率各渲染兩小時，每率 14,401 個實際起音與拍點比對，四率最大分別 0.499、0.333、0.167、0.333 ms。[逐率最大偏差](beat-long-all-rates.log) |
| B-8 | #1662 91366d09 | 軟體通過；警告政策待定 | 關閉全部 MIDI 目的地。10 ms 回呼中，20 ms 起顯示 retained，40 ms 起 unknown，60 ms 恢復。有效回呼期間 3,360 個 PCM 無斷音；模擬中斷 20 ms，和對照僅差 960 samples。實體裝置重新開啟所需時間未量。 |

## C　管弦樂與影像

| ID | PR / SHA | 判定 | 量測與歸屬 |
|---|---|---|---|
| C-1 | #1663 0819e610 | 整格定位失敗；連續追碼通過 | 6 種幀率 × 4 個取樣率，各 10 分鐘。390,996 次整格比對中，有 67,793 次，full-frame 定位比 Session Setup 早 1 sample，連續 QF 誤差 0，匹配來源沒有誤警。#1669 同一測試 390,996 次均精確，下一輪可將既有修正下移到 #1663。[上下游對照](mtc-c1-integrated.log) 例：23.976 fps、44.1 kHz 第 1 格為 1,839，Session Setup 為 1,840。#1663 紅測 `scenario_c1_c8_ten_minutes_six_rates`。 |
| C-2 | #1663 0819e610 | 通過 | 29.97 DF 在第一分鐘、十分鐘邊界顯示正確的下一格，對應 48 kHz 的相鄰取樣距離各 1,602、1,601。 |
| C-3 | #1663 0819e610 | 整點通過；午夜政策待定 | 30 fps 跨小時進 1,600 samples，跨午夜顯示歸零並保持鎖定。開放問題是工作階段要回到第 0 天，還是延續至下一天。 |
| C-4 | #1663 0819e610 | 符合已記載的重新定位策略 | ±50 ppm 各追隨兩小時，兩側均 0 次失鎖、10 次硬定位，幅度為 ±1,603 samples（33.40 ms），符合「超過一格並持續一秒才重定位」的文件規則。PCM 最大偏差 33.414／33.373 ms，追蹤區間無重複或遺漏節拍。[逐次跳幅](mtc-long-final.log) |
| C-5 | #1662 91366d09 | 輸出通過；效能門檻待定 | 四種取樣率各 24,000 pulses，經 1,000 個逐拍 tempo 事件、四種拍號。最大交付誤差 0.1248 ms；1,000 次非零定位的 SPP 全正確。48 kHz 七輪中位，密集／固定 tempo map 各 0.8344／0.4977 ms 每千次。 |
| C-6 | #1662 91366d09 | 通過 | 44.1、48、96、192 kHz 各測 5、20、30、300、999、1,000 BPM，24 組均送出各 96 pulses，最大交付誤差 0.1198 ms。 |
| C-7 | #1663 0819e610 | 軟體保有鎖定；回呼期限有超時 | 150 軌、48 kHz、128 samples，各 1,500 blocks。每軌 0／2／6 inserts，三輪都取得鎖定且 0 次失鎖。程序 CPU 為單一邏輯核心的 62.4%／101.1%／213.8%，軟體超過 2.667 ms 預算的 block 各 175／274／51。這是含 OS 排程的量測，當時另有建置；數值不宜用於比較 insert 效率。離線 mixer 沒有 ASIO xrun 計數。[CPU、期限與鎖定](c7-final.log) |
| C-8 | #1662 91366d09 / #1663 0819e610 / #1669 6b82d9bc | 輸出及突變通過；MTC 定位見 C-1 | 同一份 4,800 samples 校準值跨四率為 108.844、100、50、25 ms，符合文件的 sample-based 儲存。四率 A-2 通過。MTC full-frame 的 1 sample 差異歸 #1663；紅測與 C-1 共用。 |

## D　錄音室

| ID | PR / SHA | 判定 | 量測與歸屬 |
|---|---|---|---|
| D-1 | #1669 6b82d9bc | 通過 | 不同於專案的外部速度錄製，重開、split、heal、copy、paste、consolidate、loop 後，逐音比較 MIDI 渲染與音訊；原始 6、貼上後 12、循環後 24 對全部差 0 samples。heal 回報 1 個可合併片段。[各編輯點 PCM](studio-deterministic.log) |
| D-2 | #1669 6b82d9bc | 行為已固定；政策待定 | 本地 loop 開啟且選區 [24,000,60,000)。區內與區外的 SPP+Continue 從 36,000／120,000 起播；偏好仍開，活動 loop 均為 None。 |
| D-3 | #1663 0819e610 | Undo / redo 通過；連動政策待定 | 13 clips 均移動 86,400,000 samples。automation-follows-edit 開或關時，automation、marker、tempo 都留在原位；undo / redo 精確還原。 |
| D-4 | #1662 91366d09 / #1663 0819e610 | 通過 | 選區 48,000～96,000，pre/post 實際範圍 24,000～108,000；MTC full-frame 先於首個 QF，Beat Clock 送 SPP、Continue、Clock，至 post-roll 結束才停。[走帶入口](preroll.log) |
| D-5 | #1662 91366d09 / #1663 0819e610 / #1669 6b82d9bc | 同名裝置提議未達 | 重開保留 −2,501 samples；更名保留舊記錄，新名可設 +900。兩埠同名時設 +701、+302，僅存一筆 +302，開埠會警告。#1662 紅測 `d5_station_calibration_rename_and_same_named_units`。舊 Clock 跟隨 +480→−480，未動到獨立輸出 −200；MTC 的 +100 格→+160,000 samples 是不同設定。[跟隨遷移](d5-follow-legacy.log) |
| D-6 | #1669 6b82d9bc | 通過 | 48 kHz，輸入偏移 −12,000／0／+12,000 時，兩軌錄音起點同步為 108,000／96,000／84,000。各 6 對實際起音均同向移動，差 0 samples。 |
| D-7 | #1662 91366d09 / #1663 0819e610 / #1669 6b82d9bc | 局部恢復與提示未達 | 13 種工作站設定中 11 種型別錯誤使整份偏好載入失敗，2 種極端整數正常載入但未提示。7 種 session 故障中，3 種拒絕開啟、4 種載入但無提示；原始檔內容全部保留。工作站全份 fallback 為 main 既有行為；各 PR 擁有它引入的設定，#1663 擁有 freewheel，基礎 session 的 rate/型別讀取不專屬本堆疊。紅測 `scenario_d7_corrupt_sync_settings_recover_independently_with_diagnostics`、`scenario_d7_session_reload_recovers_sync_values_and_preserves_score`。[偏好](settings.log) · [session](session-corrupt.log) |

## E　異常與交錯輸入

| ID | PR / SHA | 判定 | 量測與歸屬 |
|---|---|---|---|
| E-1 | #1663 0819e610 / #1669 6b82d9bc | Clock 通過，MTC 失敗 | F8、FA、FC 各插入 full-frame SysEx 或 F1/data 中間。Clock 解碼正確；MTC reader 收到這種原始 payload 時 6/6 未解出時碼。作業系統可能先拆訊息。#1663 紅測 `scenario_e1_interleaved_wire_realtime`。 |
| E-2 | #1663 0819e610 | 通過 | 9 種畸形 SysEx，以及缺件、亂序、逆向 QF，均未造成走帶移動或 panic。 |
| E-3 | #1669 6b82d9bc | 通過；播放中 SPP 的政策待定 | 非法高位資料中斷 SPP；連續 SPP 16383、3 對應 98,298、18 個 pulses。Continue 從 18 開始，播放中 SPP 被略過。 |
| E-4 | #1669 6b82d9bc | 通過，已量邊界狀態 | 每 10 秒一拍鐘，60 pulses 後顯示 Coasting；每秒 10,000 pulses，100,000 筆後顯示 Locked。兩者都無有效 BPM，佇列最多 2。 |
| E-5 | #1663 0819e610 / #1669 6b82d9bc | 通過 | 每個 reader 各 10,000,000 bytes。MTC 固定結構 1,040 B，處理 1,554,172 個 payload；Clock 為 4,608 B，佇列峰值 6/32，均無 panic。 |


## 處理優先順序

1. **演出中換主鐘。** #1669 的 Coast 在無 Start 的換台模式沒有恢復鎖定，造成接近半秒的誤差；先決定純 F8 回來時的重鎖規則。A-3 有紅測。
2. **裝置恢復時送出過期控制訊息。** 首批 Clock／QF 在 100 ms 中斷後集中補發，穩定區與 200 ms 中斷測試會掩蓋這段。建議先由 #1662 的共用輸出與 Clock 游標釐清，再驗證 #1663 的 MTC encoder。A-10 有紅測。
3. **大幅變速。** #1669 的 80→130→80 數量正確，當時降速後第一個反拍早 70.104 ms。連續 ±8% 推速也超過提議的 4 ms；在調整前要保住 A-2 已通過的突然小幅變速。
4. **資料和協定相容性。** MTC reader 無法接收 E-1 的交錯封包。工作站設定只壞一項即可使整份偏好載入失敗，部分 session 設定損壞會擋住開檔；本輪未改寫受測檔。D-7 共用載入策略在 main 已存在，應先釐清共用層歸屬。
5. **可見性和精度。** #1663 的排隊錄音沒有原因提示；部分 full-frame 定位與 Session Setup 差 1 sample。#1662 的同名埠校準、停止時送 SPP，及 #1669 的本地 loop、逐筆 note-off、六小時 tempo 歷史，均有數據可供決策。

## 重跑與證據範圍

把各支本機 patch 套在表列原始 SHA 後，依 [#1662 指令](beat.md)、[#1663 指令](mtc.md)、[#1669 指令](follow.md) 執行。紅測應回傳失敗碼。工作站與錄音室的補充命令如下。

~~~text
cargo test -p soundcraft --bin soundcraft scenario_d7 -- --nocapture
cargo test -p soundcraft-engine --lib scenario_d7_session -- --nocapture
cargo test -p soundcraft-ui-egui --lib scenario_studio -- --nocapture --test-threads=1
cargo test -p soundcraft-playback --lib scenario_a10 -- --nocapture --test-threads=1
cargo test -p soundcraft-ui-egui --lib scenario_c7_chase -- --ignored --nocapture --test-threads=1
~~~

錄音測試的音訊經真正的 WAV writer 寫檔；模擬 MIDI 注入點是輸入回呼給錄音器的時間戳。首次測試把超過 ring 容量的虛擬輸入無間隔塞進背景 writer，造成音訊尾段人為消失。先以分批餵入排除測試機制造成的假象，最後使用總長小於 ring 容量的 fixture，消除對背景執行緒排程與 sleep 的依賴。B-6、D-1、D-6、C-8 四項同一次執行通過。[分批對照](studio-rerun.log) · [最終確定性測試](studio-deterministic.log)。C-7 的軟體期限超時無法直接推算喇叭掉音。這輪未作實機驗收，前次 Model 12 的結果沒有納入本輪數據。

## 可選實機補驗

只有下列測試能增加軟體回歸無法提供的證據，可於方便時同一時段完成。

| 情境 | 起始設定與自動流程 | 時間 | 可以省略的理由 |
|---|---|---|---|
| A-10／B-8 實體輸出 | 開始前一次接好 Model 12 與 UM-ONE 的回送，選定 ASIO 路由及安全監聽音量。之後由程式自動關閉／重開音訊串流，雙協定持續運作，同步錄 MIDI 和 MAIN，無須中途拔插。 | 約 5 分鐘 | 軟體已區分失效 100／200 ms 及穩定期；只有要判斷這台驅動實際產生哪一種中斷，以及是否可聽，才需執行。 |
| C-4 長時時碼 | 開始前一次接好 Model 12 MIDI OUT → UM-ONE，設定可連播的長歌曲和 MTC，啟動一次播放。其後由軟體自行監看與回錄。 | 約 2 小時，可無人值守 | 模擬已量出 ±50 ppm 每側 10 次跳轉與實際 PCM 誤差；硬體只補這台裝置的實際漂移量。 |

## 外部時鐘抖動、持續推速與裝置提前量

#1669 後續驗收採實際 PCM 起音與尾音比對。±8% 連續推速峰值降到 3.8333 ms。穩速且符合預測條件的 10 格均為零取樣偏差，減速後第一下反拍介於 −25.000 到 +86.500 ms。集中送達另測到 180→60 BPM 提早 196.896 ms。逐音紀錄和完整 18 格對照收在[本機驗收報告](../g11-clock-stress/REPORT.zh-TW.md)。
