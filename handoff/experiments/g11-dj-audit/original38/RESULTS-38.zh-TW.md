# 第一次 38 項情境測試完整結果

原始規格共有 A 組 10 項、B 組 8 項、C 組 8 項、D 組 7 項、E 組 5 項。下表按首次執行的原始 head 彙整，每項對照原始需求和測試紀錄。本表沒有以後來的修正重寫當時結果。額外的 24 小節 EDM 為附加案例，不計入 38 項。

依原始驗收條件逐項劃分，24 項通過、11 項有至少一個斷言或指定目標未達、3 項僅能部分驗證。報告政策或現況的題目，完成觀察即可通過；未達提議門檻的項目不代表違反 MIDI 規格。C-8 重複計到 C-1 的整格問題，失敗項數不等於獨立缺陷數。

| 首次版本 | 提交 | 本機測試補丁 |
|---|---|---|
| #1662 | `91366d09fd5f925492152c00be914d7dff7c0330` | [單支補丁](../../g11-scenarios-20261122/local-tests-1662.patch) |
| #1663 | `0819e6101d115e9bc2f1e61e2cfac66c9a2731f1` | [單支補丁](../../g11-scenarios-20261122/local-tests-1663.patch) |
| #1669 | `6b82d9bc84af17b259b98970dc5557a93c80d7a0` | [單支補丁](../../g11-scenarios-20261122/local-tests-1669.patch) |

## 最常被誤讀的四項

- **惡意輸入**：E-1 的測試斷言因 6/6 MTC 無法解碼而 panic。被測解碼器在這些輸入下本身沒有 panic。另有 9 組畸形 SysEx、缺件／亂序／逆向 QF、極端 Clock 速率及兩個 reader 各一千萬 bytes 的 seeded 輸入，均未觸發產品 panic。這是測過的輸入範圍。
- **午夜**：30 fps、48 kHz，滾動時碼跨午夜的四個位置為 4,147,196,400 → 4,147,199,600 → 2,800 → 6,000 samples，保持鎖定；顯示與專案定位回繞當日。要不要維持跨日專案位置仍是 #1663 的政策問題。
- **兩小時漂移**：兩次各自模擬兩小時。−50 ppm 時 14,396 個節拍、峰值 33.414 ms、末拍 +26.039 ms、10 次 +1,603 samples 硬定位；+50 ppm 時 14,397 個節拍、峰值 33.373 ms、末拍 −26.020 ms、10 次 −1,603 samples 硬定位。兩組均 0 次失鎖、漏拍與重複。另有 B-7 四種取樣率各兩小時的 Beat Clock 輸出測試。
- **音訊輸出時間警告**：A-10 雙輸出時，0 ms 正常、250 ms retained、300 ms unknown、500 ms 清除；B-8 無 MIDI 目的地且回呼每 10 ms，到 20 ms 顯示 retained、40 ms 顯示 unknown、60 ms 清除。這些是兩個測試劇本上的時間點，並非套用到所有裝置的固定 timeout。

## 逐項結果

表內時間和聲音數字取自當時的模擬時鐘、MIDI 交付、渲染 PCM 或錄音 WAV；各案例的方法請見原始 log。PR 欄列出當時的程式來源，其中跨層案例在觀察欄說明最低歸屬。原驗收文字保留英文，以免門檻或範圍在翻譯時改變。


### A．DJ

| ID | 首次 PR / head | 原驗收條件 | 判定 | 首次實測數字／限制 | 原始紀錄 |
|---|---|---|---|---|---|
| A-1 | #1669 6b82d9bc | Every hi-hat within 4 ms of the master grid; no tempo-readout flicker larger than 0.1 BPM; no tempo-step recovery triggered by a ramp | **未全數通過**（提議未達） | 124→124.3→124 BPM 最大 3.792 ms；±8% 長推速最大 9.062 ms，理想無抖動也達 8.979 ms。9 組皆 0 次誤判 step。第一拍後顯示變化 ≤0.091 BPM，取得期最大 7.226。#1669 紅測 `scenario_a1_pitch_fader_rendered_hats`。 | [紀錄1](../../g11-scenarios-20261122/follow-ui-final.log) |
| A-2 | #1669 6b82d9bc | Signed error of every 8th-note event for the first 8 beats after the step. Proposed target: first offbeat ≤ 10 ms, from beat 2 on ≤ 4 ms | **通過**（通過） | 四種取樣率 × 兩個方向 × 拍頭／拍中，16 組。128↔140 BPM 首個八分音符 −4.312～+3.492 ms，其後最大 0.750 ms。 | [紀錄1](../../g11-scenarios-20261122/follow-ui-final.log) |
| A-3 | #1669 6b82d9bc | Behaviour matches the selected loss mode (Coast / Stop); after resume, no duplicate or missing notes; the phase settles within the A-2 target; the state shown to the user is correct | **未全數通過**（Coast 未重新鎖定） | 300 ms 斷鐘後只恢復 F8 並從 120 變 128。65 個音都在，末音晚 473.438 ms，狀態仍是 Coasting。Stop 策略約在 8.137 s 停下。#1669 紅測 `scenario_a3_resume_pulses_without_start`。 | [紀錄1](../../g11-scenarios-20261122/follow-ui-final.log) |
| A-4 | #1669 6b82d9bc | Lock is held; tempo readout steady; no tempo-step false positives (count them) | **通過**（通過） | 3、4、5 pulse 三種群聚各 10 分鐘、28,800 pulses。0 次掉鎖，取得期後 0 次假變速。穩定區讀值總範圍 119.9710～120.0484 BPM。 | [紀錄1](../../g11-scenarios-20261122/follow-reader.log) |
| A-5 | #1669 6b82d9bc / main | Every Start begins at bar 1 beat 1, every Continue at the last SPP; no stuck notes (note-off for every note-on) | **未全數通過**（起點通過；逐一 note-off 提議未達） | 50 Start 全部歸零、50 Continue 全部從 SPP；100 NoteOn 對 58 個明確 NoteOff，另 42 個由 plugin reset 釋音，0 個持續發聲。現有 main 也在 Stop 時 reset；外部硬體卡音未經證實。紅測 `scenario_a5_notes_released_across_random_stops`。 | [紀錄1](../../g11-scenarios-20261122/follow-reader.log) |
| A-6 | #1669 6b82d9bc | No drift growth; memory and queue lengths bounded (report the maximum); no audio-thread allocation if the crate has a check for it | **部分驗證**（六小時完成；記憶體上界待定） | 1,168,942 pulses、63 次變速。六個整時前的 PCM 起音 −1.667～+2.562 ms，沒有累積漂移趨勢；穩定區網格最大 4.688 ms。單次最多 2 個 transport 動作，tempo 歷史自第一小時 529 增至 2,703 筆（有效內容 43,248 B）。未量配置器總量或證明回呼零配置。 | [紀錄1](../../g11-scenarios-20261122/follow-long-final.log) |
| A-7 | #1662 91366d09 | Each port's pulses land at grid + its offset within 1 ms in the capture sink; the cap is honoured | **通過**（通過） | 三個埠 −250、0、+250 ms，四種取樣率，最大實際交付誤差 0.494 ms；48 kHz 超額要求截在 ±12,000 samples。 | [紀錄1](../../g11-scenarios-20261122/beat-final.log) |
| A-8 | #1662 91366d09 | Status line shows the loss; other ports keep sending; on return, sending resumes at the right phase and the first message is not a stale burst | **通過**（模擬通過） | A 埠在第八次 Clock 傳送失敗時回報斷線，B 繼續送出 63 個 F8。A 重開以 SPP 10、Continue、Clock 開始，首個 Clock 排定位置誤差 0 µs、實際交付晚 0.572 ms，後續最短實際間隔 20.506 ms。 實體 USB 拔插不在這一項模擬範圍。 | [紀錄1](../../g11-scenarios-20261122/beat-final.log)、[紀錄2](../../g11-scenarios-20261122/beat-status-line.log) |
| A-9 | #1663 0819e610 | Every relocate sends one full-frame at the new position, then contiguous quarter frames; no backward quarter frames; no extra full-frame during steady play | **通過**（通過） | 20 次演出中跳 cue，20 個 full-frame、790 個順序正確的 quarter-frame。最慢 190 ms 重新鎖定。 | [紀錄1](../../g11-scenarios-20261122/mtc-restarts.log) |
| A-10 | #1662 91366d09 / #1663 0819e610 | Audio continues; output timing goes unknown then recovers; record when the output-timing warning appears and clears (the intended rule for this warning is still being decided; just report); after recovery both outputs are back within 1 ms | **未全數通過**（復原首批提議未達；穩定後通過） | 200 ms 未知後，0 筆過期交付，Clock 在恢復當下送出、MTC 在其後 40 ms 從新的群組起送。雙輸出重設，96,000 個 PCM 值和對照相同。250 ms 顯示保留延遲、300 ms 未知、500 ms 恢復；600 ms 起 Clock/MTC 交付最差 0.833/0 ms。在另一個 100 ms 未知區間，期間 0 筆，恢復當下 Clock/MTC 過期 95.833/100 ms；排定時間仍在格上。Clock 的游標與共用輸出在 #1662，MTC encoder 在 #1663。#1662 獨立紅測 `a10_first_clock_after_unknown_lead_is_handed_off_on_time` 也送出五個過期 F8（實交在 200、201、202、203、204 ms），確認 Clock 問題來自 #1662。整合紅測 `scenario_a10_dual_encoder_recovers_after_midroll_invalid_timestamp`。 | [紀錄1](../../g11-scenarios-20261122/beat-a10.log)、[紀錄2](../../g11-scenarios-20261122/a10-final.log)、[紀錄3](../../g11-scenarios-20261122/mtc-a10d4-final.log)、[紀錄4](../../g11-scenarios-20261122/mtc-short.log) |

### B．樂團

| ID | 首次 PR / head | 原驗收條件 | 判定 | 首次實測數字／限制 | 原始紀錄 |
|---|---|---|---|---|---|
| B-1 | #1662 91366d09 | Clock pulses follow the ramp (pulse interval error ≤ 0.5 ms against the tempo map); SPP sent on every locate matches the marker position in 16ths (MIDI spec: 1 MIDI beat = 6 clocks) | **未全數通過**（播放通過；停止定位提議未達） | 12 首歌單，48 kHz 的 4,608 個 pulses 最大間隔誤差 0.1042 ms。11 個非零位置重新播放均送正確 SPP；停止中換到同樣位置 0/11 送出。#1662 紅測 `b1_stopped_setlist_locates_send_marker_spp`。 | [紀錄1](../../g11-scenarios-20261122/beat-final.log) |
| B-2 | #1663 0819e610 | Full-frame then quarter frames each time; a chasing receiver (our own #1663 reader) relocks within the Freewheel setting and never jumps backwards during steady play | **通過**（通過） | 25 fps 倒回八小節再播 30 次，30 個 full-frame 後依序送出 48,000 個 quarter-frame，最慢 150 ms 重鎖，低於 8 frames 的 320 ms。 另記錄到停止中定位的 30 個 full-frame。 | [紀錄1](../../g11-scenarios-20261122/mtc-restarts.log) |
| B-3 | #1663 0819e610 | B behaves exactly as the guide describes for that mode (cite the page); with Jam Sync, B keeps playing in time; report the drift after 10 s | **通過**（通過；單列失碼偵測時間） | 25 fps，從最後收到的完整位置到停播，None / Frames 4 / 8 / 40 分別為 80 / 160 / 320 / 1,600 ms。None 的 80 ms 是辨識失碼的時間；Jam Sync 續播 10 秒，理想同速時差 0 sample。對照《Pro Tools Reference Guide 2026.4》印刷頁 1819 的 MTC、Frames、Jam Sync。 | [紀錄1](../../g11-scenarios-20261122/mtc-short.log) |
| B-4 | #1663 0819e610 | Recording is allowed and the take lines up with the timeline (sample offset constant); MTC output is unaffected by the record start | **通過**（通過） | 產生 MTC、Online 關閉，兩個實際 WAV 的 6 個錄音起音與預期各差 0 samples。開錄前後同一條傳送序列共 1 FF、200 QF，10 ms 間隔。 | [紀錄1](../../g11-scenarios-20261122/mtc-short.log)、[紀錄2](../../g11-scenarios-20261122/mtc-b4-host.log) |
| B-5 | #1663 0819e610 | Refused every time, each time with a visible message (a silent refusal counts as a failure); nothing is written to disk | **未全數通過**（拒錄與資料保護通過；提示失敗） | 面板、快捷鍵、已排隊的 Record 三路均未寫檔。排隊路徑留下空白狀態，未顯示原因。#1663 紅測 `scenario_b5_three_online_record_requests`。 | [紀錄1](../../g11-scenarios-20261122/mtc-b5-verified.log) |
| B-6 | #1669 6b82d9bc | Recording allowed (agreed design); MIDI and audio stay aligned after disabling follow, save and reopen (±1 sample in the render) | **通過**（通過） | 100→120 BPM 跟鐘時同步錄音訊與 MIDI，關閉跟隨、存檔重開後分軌渲染。6 對起音的差全為 0 samples。 | [紀錄1](../../g11-scenarios-20261122/studio-deterministic.log) |
| B-7 | #1662 91366d09 | Clock out stays aligned to the **audible** output, including the system delay: pulse vs rendered click ≤ 1 ms | **通過**（通過） | 2,048 samples PDC，四種取樣率各渲染兩小時，每率 14,401 個實際起音與拍點比對，四率最大分別 0.499、0.333、0.167、0.333 ms。 | [紀錄1](../../g11-scenarios-20261122/beat-long-all-rates.log) |
| B-8 | #1662 91366d09 | Record whether a warning bar appears (the rule is still being decided; just report); audio recovers automatically; no audible gap longer than the reopen itself (report ms) | **通過**（軟體通過；警告政策待定） | 關閉全部 MIDI 目的地。10 ms 回呼中，20 ms 起顯示 retained，40 ms 起 unknown，60 ms 恢復。有效回呼期間 3,360 個 PCM 無斷音；模擬中斷 20 ms，和對照僅差 960 samples。實體裝置重新開啟所需時間未量。 | [紀錄1](../../g11-scenarios-20261122/beat-final.log) |

### C．影像與管弦樂

| ID | 首次 PR / head | 原驗收條件 | 判定 | 首次實測數字／限制 | 原始紀錄 |
|---|---|---|---|---|---|
| C-1 | #1663 0819e610 | Locked position equals the timecode-to-sample conversion used by Session Setup (exactly, at whole frames); rate-mismatch warning only on a real mismatch | **未全數通過**（整格定位失敗；連續追碼通過） | 6 種幀率 × 4 個取樣率，各 10 分鐘。390,996 次整格比對中，有 67,793 次，full-frame 定位比 Session Setup 早 1 sample，連續 QF 誤差 0，匹配來源沒有誤警。#1669 同一測試 390,996 次均精確，下一輪可將既有修正下移到 #1663。上下游對照 例：23.976 fps、44.1 kHz 第 1 格為 1,839，Session Setup 為 1,840。#1663 紅測 `scenario_c1_c8_ten_minutes_six_rates`。 | [紀錄1](../../g11-scenarios-20261122/mtc-short.log)、[紀錄2](../../g11-scenarios-20261122/mtc-c1-integrated.log) |
| C-2 | #1663 0819e610 | No skipped or doubled frame in the displayed counter; the sample position is continuous (MTC spec drop-frame rule) | **通過**（通過） | 29.97 DF 在第一分鐘、十分鐘邊界顯示正確的下一格，對應 48 kHz 的相鄰取樣距離各 1,602、1,601。 | [紀錄1](../../g11-scenarios-20261122/mtc-short.log) |
| C-3 | #1663 0819e610 | Hour wrap handled as the guide/spec says; if neither defines midnight wrap behaviour for chase, record the current behaviour as an Open question | **通過**（整點通過；午夜政策待定） | 30 fps 跨小時進 1,600 samples，跨午夜顯示歸零並保持鎖定。開放問題是工作階段要回到第 0 天，還是延續至下一天。 午夜的連續 QF 跨界值為 4,147,199,600 → 2,800 samples。 | [紀錄1](../../g11-scenarios-20261122/mtc-short.log) |
| C-4 | #1663 0819e610 | Chase stays locked; any correction is smooth or happens as documented; report the maximum offset and the number and size of any relocates | **通過**（符合已記載的重新定位策略） | ±50 ppm 各追隨兩小時，兩側均 0 次失鎖、10 次硬定位，幅度為 ±1,603 samples（33.40 ms），符合「超過一格並持續一秒才重定位」的文件規則。PCM 最大偏差 33.414／33.373 ms，追蹤區間無重複或遺漏節拍。 | [紀錄1](../../g11-scenarios-20261122/mtc-long-final.log) |
| C-5 | #1662 91366d09 | Every pulse within 0.5 ms of the map; SPP after a locate inside an odd meter equals the position in 16ths; no slowdown in map lookup (time 1,000 locates) | **部分驗證**（輸出通過；效能門檻待定） | 四種取樣率各 24,000 pulses，經 1,000 個逐拍 tempo 事件、四種拍號。最大交付誤差 0.1248 ms；1,000 次非零定位的 SPP 全正確。48 kHz 七輪中位，密集／固定 tempo map 各 0.8344／0.4977 ms 每千次。 密集查找較固定速度慢約 0.337 ms/1,000 次，無量化效能門檻。 | [紀錄1](../../g11-scenarios-20261122/beat-final.log) |
| C-6 | #1662 91366d09 | No panic, no division by zero, pulses correct or clamped as documented | **通過**（通過） | 44.1、48、96、192 kHz 各測 5、20、30、300、999、1,000 BPM，24 組均送出各 96 pulses，最大交付誤差 0.1198 ms。 | [紀錄1](../../g11-scenarios-20261122/beat-final.log) |
| C-7 | #1663 0819e610 | No lock loss caused by UI or render load; report the CPU and any xruns | **部分驗證**（軟體保有鎖定；回呼期限有超時） | 150 軌、48 kHz、128 samples，各 1,500 blocks。每軌 0／2／6 inserts，三輪都取得鎖定且 0 次失鎖。程序 CPU 為單一邏輯核心的 62.4%／101.1%／213.8%，軟體超過 2.667 ms 預算的 block 各 175／274／51。這是含 OS 排程的量測，當時另有建置；數值不宜用於比較 insert 效率。離線 mixer 沒有 ASIO xrun 計數。 超時不能推算實際裝置掉音數。 | [紀錄1](../../g11-scenarios-20261122/c7-final.log) |
| C-8 | #1662 91366d09 / #1663 0819e610 / #1669 6b82d9bc | Offsets stored in samples keep the same time in ms when the session rate changes, or the change is documented; MTC and clock tests above pass at each rate | **未全數通過**（輸出及突變通過；MTC 定位見 C-1） | 同一份 4,800 samples 校準值跨四率為 108.844、100、50、25 ms，符合文件的 sample-based 儲存。四率 A-2 通過。MTC full-frame 的 1 sample 差異歸 #1663；紅測與 C-1 共用。 | [紀錄1](../../g11-scenarios-20261122/beat-final.log)、[紀錄2](../../g11-scenarios-20261122/mtc-short.log)、[紀錄3](../../g11-scenarios-20261122/mtc-c1-integrated.log)、[紀錄4](../../g11-scenarios-20261122/studio-deterministic.log) |

### D．錄音室

| ID | 首次 PR / head | 原驗收條件 | 判定 | 首次實測數字／限制 | 原始紀錄 |
|---|---|---|---|---|---|
| D-1 | #1669 6b82d9bc | MIDI attacks match the audio attacks ±1 sample in the render after every step | **通過**（通過） | 不同於專案的外部速度錄製，重開、split、heal、copy、paste、consolidate、loop 後，逐音比較 MIDI 渲染與音訊；原始 6、貼上後 12、循環後 24 對全部差 0 samples。heal 回報 1 個可合併片段。 | [紀錄1](../../g11-scenarios-20261122/studio-deterministic.log) |
| D-2 | #1669 6b82d9bc | Report the current behaviour (today the local loop appears to be ignored while following), pin it with a test, and list it as an Open question | **通過**（行為已固定；政策待定） | 本地 loop 開啟且選區 [24,000,60,000)。區內與區外的 SPP+Continue 從 36,000／120,000 起播；偏好仍開，活動 loop 均為 None。 | [紀錄1](../../g11-scenarios-20261122/follow-ui-final.log) |
| D-3 | #1663 0819e610 | Report what moves (clips, automation, markers, tempo map) with the setting on and off; the intended automation rule is still being decided. Undo restores clips (and automation, if moved) exactly | **通過**（Undo / redo 通過；連動政策待定） | 13 clips 均移動 86,400,000 samples。automation-follows-edit 開或關時，automation、marker、tempo 都留在原位；undo / redo 精確還原。 | [紀錄1](../../g11-scenarios-20261122/mtc-d3.log) |
| D-4 | #1662 91366d09 / #1663 0819e610 | Output starts at the pre-roll position; full-frame before the first quarter frame | **通過**（通過） | 選區 48,000～96,000，pre/post 實際範圍 24,000～108,000；MTC full-frame 先於首個 QF，Beat Clock 送 SPP、Continue、Clock，至 post-roll 結束才停。 | [紀錄1](../../g11-scenarios-20261122/preroll.log)、[紀錄2](../../g11-scenarios-20261122/mtc-d4-host.log)、[紀錄3](../../g11-scenarios-20261122/mtc-a10d4-final.log)、[紀錄4](../../g11-scenarios-20261122/beat-final.log) |
| D-5 | #1662 91366d09 / #1663 0819e610 / #1669 6b82d9bc | The offset follows the right port; a missing port is reported, not silently remapped; legacy input offsets migrate with the documented sign change | **未全數通過**（同名裝置提議未達） | 重開保留 −2,501 samples；更名保留舊記錄，新名可設 +900。兩埠同名時設 +701、+302，僅存一筆 +302，開埠會警告。#1662 紅測 `d5_station_calibration_rename_and_same_named_units`。舊 Clock 跟隨 +480→−480，未動到獨立輸出 −200；MTC 的 +100 格→+160,000 samples 是不同設定。 | [紀錄1](../../g11-scenarios-20261122/beat-settings-final.log)、[紀錄2](../../g11-scenarios-20261122/beat-final.log)、[紀錄3](../../g11-scenarios-20261122/d5-follow-legacy.log)、[紀錄4](../../g11-scenarios-20261122/mtc-d5.log) |
| D-6 | #1669 6b82d9bc | The recorded take position moves by exactly the offset | **通過**（通過） | 48 kHz，輸入偏移 −12,000／0／+12,000 時，兩軌錄音起點同步為 108,000／96,000／84,000。各 6 對實際起音均同向移動，差 0 samples。 | [紀錄1](../../g11-scenarios-20261122/studio-deterministic.log) |
| D-7 | #1662 91366d09 / #1663 0819e610 / #1669 6b82d9bc | No panic; a lenient default with a visible note; nothing else in the session is lost | **未全數通過**（局部恢復與提示未達） | 13 種工作站設定中 11 種型別錯誤使整份偏好載入失敗，2 種極端整數正常載入但未提示。7 種 session 故障中，3 種拒絕開啟、4 種載入但無提示；原始檔內容全部保留。工作站全份 fallback 為 main 既有行為；各 PR 擁有它引入的設定，#1663 擁有 freewheel，基礎 session 的 rate/型別讀取不專屬本堆疊。紅測 `scenario_d7_corrupt_sync_settings_recover_independently_with_diagnostics`、`scenario_d7_session_reload_recovers_sync_values_and_preserves_score`。 | [紀錄1](../../g11-scenarios-20261122/settings.log)、[紀錄2](../../g11-scenarios-20261122/session-corrupt.log) |

### E．異常輸入

| ID | 首次 PR / head | 原驗收條件 | 判定 | 首次實測數字／限制 | 原始紀錄 |
|---|---|---|---|---|---|
| E-1 | #1663 0819e610 / #1669 6b82d9bc | Both the clock and the MTC message are decoded correctly | **未全數通過**（Clock 通過，MTC 失敗） | F8、FA、FC 各插入 full-frame SysEx 或 F1/data 中間。Clock 解碼正確；MTC reader 收到這種原始 payload 時 6/6 未解出時碼。作業系統可能先拆訊息。#1663 紅測 `scenario_e1_interleaved_wire_realtime`。 未觀察產品 panic，失敗是測試斷言。 | [紀錄1](../../g11-scenarios-20261122/mtc-e.log)、[紀錄2](../../g11-scenarios-20261122/follow-e.log) |
| E-2 | #1663 0819e610 | Rejected or ignored without moving the transport; no panic | **通過**（通過） | 9 種畸形 SysEx，以及缺件、亂序、逆向 QF，均未造成走帶移動或 panic。 | [紀錄1](../../g11-scenarios-20261122/mtc-e.log) |
| E-3 | #1669 6b82d9bc | Handled as the MIDI spec says (SPP is ignored while playing on most devices; if the spec is silent, record the behaviour as an Open question) | **通過**（通過；播放中 SPP 的政策待定） | 非法高位資料中斷 SPP；連續 SPP 16383、3 對應 98,298、18 個 pulses。Continue 從 18 開始，播放中 SPP 被略過。 | [紀錄1](../../g11-scenarios-20261122/follow-e.log) |
| E-4 | #1669 6b82d9bc | No panic, no unbounded queue, state reported to the user | **通過**（通過，已量邊界狀態） | 每 10 秒一拍鐘，60 pulses 後顯示 Coasting；每秒 10,000 pulses，100,000 筆後顯示 Locked。兩者都無有效 BPM，佇列最多 2。 | [紀錄1](../../g11-scenarios-20261122/follow-e.log) |
| E-5 | #1663 0819e610 / #1669 6b82d9bc | No panic; memory bounded | **通過**（通過） | 每個 reader 各 10,000,000 bytes。MTC 固定結構 1,040 B，處理 1,554,172 個 payload；Clock 為 4,608 B，佇列峰值 6/32，均無 panic。 | [紀錄1](../../g11-scenarios-20261122/mtc-e.log)、[紀錄2](../../g11-scenarios-20261122/follow-e.log) |

## 歷史結果與後續版本的界線

首次 A-3 的 473.438 ms 和 A-10 的過期補送都有後續複驗。A-1 後來的 ±8% PCM 峰值為 3.8333 ms。其他早期未達、政策問題和效能數字只對表列版本負責；這張表沒有把所有歷史缺陷算成現行 head 的缺陷。[A-3 前後對照](../../g11-coast-verification/REPORT.zh-TW.md) · [A-10 前後對照](../../g11-a10-recovery/REPORT.zh-TW.md) · [後續時序量測](../../g11-clock-stress/REPORT.zh-TW.md)

[首次完整報告](../../g11-scenarios-20261122/REPORT.zh-TW.md) · [Clock 輸出量測](../../g11-scenarios-20261122/beat.md) · [MTC 量測](../../g11-scenarios-20261122/mtc.md) · [Clock 跟隨量測](../../g11-scenarios-20261122/follow.md)
