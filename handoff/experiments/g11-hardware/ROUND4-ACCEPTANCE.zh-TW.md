# G-11 最終實機驗收表

2026-11-20 21:22 Windows 列出 UM-ONE、Model 12 MIDI、MIDIIN2／MIDIOUT2 (Model 12 MIDI)，以及 Model 12 音訊輸入與輸出。Model 12 音訊裝置的驅動為 TEAC 14.30.55.883。後續實測確認錄音機從 SD 播放，DIN OUT 接 UM‑ONE；實際走線與各次量測列於下方。[唯讀盤點 JSON](round4-enumeration-20261120-212236.json)

[STORAGE 自動恢復三輪](h-mtc-sd-phase-20261121/REPORT.zh-TW.md)：正式版在同一程序回到原裝置，三次 A4 為 +3.321、+3.183、+3.181 ms。當次基準為 +3.810 ms；舊環境的 11.619 ms 絕對比較帶未達標。

## #1663 的 N-7 實機驗收

2026-11-20，使用 Windows 桌面版 `006a968d7a304c155f2edd82fba3bcab8fb6c4f2`。測試專案為 48 kHz，起始時碼 00:00:00:00。Model 12 在本體錄音機模式播放 30 fps non-drop 時碼，背面 MIDI OUT 接 UM-ONE。每輪保持 USB 連線和本體播放，只有五針 MIDI 線拔下再接回。診斷記錄含查詢起訖時間及播放游標。[執行檔 SHA-256](round4-006a968-sha256.txt)

| 模式 | 斷線期間 | 插回後 |
|---|---|---|
| None | 最後收到 00:00:14:02，顯示時碼遺失並停播。進入 freewheel 次數增加 0。 | 在 00:00:18:22 重新鎖定，恢復播放。[逐筆診斷](round4-006a968-none.jsonl) |
| Frames，8 frames | 時碼停在 00:00:07:22，SoundCraft 繼續播放；觀測到 0/8 至 7/8，接著停播。第一次觀測到 0/8 到首次回報停止相隔 248 ms。 | 首次接回後有短暫再失鎖，至 00:00:14:18 恢復穩定。這次記錄無法判定短暫失鎖的來源。[逐筆診斷](round4-006a968-frames8.jsonl) |
| Jam Sync | 最後收到 00:00:12:02；從進入內部時鐘到重新鎖定，兩次狀態觀測相隔 14.567 秒。中間的播放游標由 594,380 前進至 1,285,100 samples。 | 在 00:00:26:20 接回，期間 hard relocates 計數維持 2。Model 12 停止送碼後 SoundCraft 繼續播放；關閉 Online 後確認播放停止。[逐筆診斷](round4-006a968-jam.jsonl) |

這三輪驗證了使用者拔插時的播放、停止和恢復。248 ms 是應用程式輪詢所得的間隔；8 frames 在 30 fps 等於 266.7 ms。精確的中斷門檻、短於上限時的恢復與損壞時碼的處理另以回歸測試驗證。以下各列列出其餘情境及設備條件。[歷史報告](REPORT.zh-TW.md)

## #1663 的 H-MTC-SD：本體錄 SD 並發送 MTC

**2026-11-21 實測完成。** Model 12 錄 SD 時會從 DIN 發送 MTC。SoundCraft 三輪都鎖定、播放伴奏並跟停。三輪的伴奏起音偏差極差為 **42.0 ms**，未達「跨次偏差固定」的驗收條件。

Model 12 韌體為 1.30 0088，歌曲為 48 kHz／24-bit，MIDI TIMECODE 開啟、MIDI CLOCK/SPP 關閉。背面 DIN OUT 經 Roland UM‑ONE 進入 SoundCraft。CH1 以 LIVE 錄麥克風，CH2 以 PC 錄 S‑MU2000 的 USB 回送，兩軌分開寫入同一首 SD 歌曲。SoundCraft 執行版為 #1663 的 `ee80920`，專案以 30 fps non-drop、零起始時碼和零外部偏移跟播，Online 開啟、Gen MTC 關閉、Freewheel 設 Frames 8。[執行檔與專案雜湊](h-mtc-sd-20261121-211205/control.json) · [設定讀回](h-mtc-sd-20261121-211205/reader-arm.json)

1. **先驗發碼。** 讓現場聲源與伴奏回送兩路進入 SD 錄音待命，以走帶區 ● 開錄並確認計數前進。檢查 UM‑ONE／WinMM 的時間戳記與連續前進的 MTC quarter-frame。若沒有，先在同一條線、同一埠、同一擷取設定下，驗證普通 ▶ 播放確實收到時碼。若播放有碼、再錄音仍無碼，停在此步，記錄本次韌體與設定下的 Model 12 行為。若播放也無碼，列為擷取或接線尚待確認。
2. **共三次，每次至少 60 秒。** 可依序用歌頭、非零位置、歌頭起錄。保留各次的兩路 SD 原檔、起錄絕對位置、MTC 封包與 SoundCraft 走帶紀錄。第三次在已鎖定時，只拔 DIN 線約 1 秒後插回，兩台的 USB 與本體錄音保持原狀。
3. **每次核對。** SoundCraft 應鎖定、跟播並在本體停止後跟停，全程沒有進入錄音或顯示應用程式錯誤。SD 兩路均須有可辨識的聲音。若 WAV 起點相對於 take，先加回起錄的歌曲位置。用同一個起音判讀方式，比較伴奏的實測位置與專案排定位置；記每輪帶正負號的偏差和三輪極差（最大值減最小值）。附件未指定毫秒容差，記錄量測解析度後再判讀穩定性。
4. **拔線輪。** 記最後一筆有效時碼、Freewheel、停播、重新鎖定及恢復播放的位置。30 fps 下 8 格約 266.7 ms；約 1 秒的斷線應足以讓 8 格用完。聽取 SD 伴奏軌，在拔線與重新定位處分別標記預期的停頓，以及接回時是否另有可聞跳音。

| SD 歌曲 | 起錄位置 | 實錄時長 | DIN quarter-frame 筆數 | SoundCraft 跟停位置 | CH2 的 A4 起音 | 相對 5.000 秒 |
|---|---|---:|---:|---|---:|---:|
| [040208_0004](h-mtc-sd-20261121-211205/take1-sd.json) | 歌頭 | 69.552 s | 8,344 | 00:01:09:16 | 5.0135 s | +13.5 ms |
| [040208_0007](h-mtc-sd-20261121-211205/take2r-sd.json) | 00:00:02:00 | 65.680 s | 7,880 | 00:01:07:20 | 5.0515 s | +51.5 ms |
| [040208_0009](h-mtc-sd-20261121-211205/take3r-sd.json) | 歌頭，中途拔 DIN | 65.640 s | 7,662 | 00:01:05:19 | 5.0555 s | +55.5 ms |

三輪走帶輪詢的錄音旗標均為 false，查詢錯誤與幀率警告均為零。SD 原檔與本機副本已逐檔核對 SHA-256。0007 的起錄位置經 Reader 確認為 96,000 samples；其 WAV 含歌頭至第 2 秒的留白，全長 67.680 秒，表中起音均以歌曲時間計算。先前的 0005、0006 只有 MAIN 有資料，CH1、CH2 WAV 為空，故未納入起音統計。[歌頭走帶](h-mtc-sd-20261121-211205/take1-mtc.json) · [非零起點走帶](h-mtc-sd-20261121-211205/take2r-mtc.json) · [拔線走帶](h-mtc-sd-20261121-211205/take3r-mtc.json)

**起音與錄音品質。** CH2 三輪都辨識到 440.92 Hz 的 A4。以 1 ms RMS 視窗量得極差 42.0 ms，再以同一段 75 ms 鋼琴起音波形交叉比對，極差為 41.75 ms。兩種方法都顯示跨次起音會變動。目前量到的是整條回送路徑，無法單獨歸因於 MTC、音訊驅動或 Model 12。CH1 前兩輪麥克風峰值為 −38.42、−37.05 dBFS；第三輪檔案完整，但峰值僅 −89.08 dBFS，無法確認該輪口述清晰度。[第一輪音訊](h-mtc-sd-20261121-211205/take1-audio.json) · [第二輪音訊](h-mtc-sd-20261121-211205/take2r-audio.json) · [第三輪音訊](h-mtc-sd-20261121-211205/take3r-audio.json) · [波形交叉比對](h-mtc-sd-20261121-211205/anchor-crosscheck.json)

**拔線與重聽。** 0009 在第一筆 quarter-frame 後 10.9496 秒失去 DIN 訊號，12.7079 秒收到下一筆，空檔 1.758 秒。最後一筆有效碼後 268.19 ms 的輪詢仍在 8/8，335.05 ms 時已停在同一游標；接回後 310.76 ms 的輪詢已鎖定並播放。輪詢間隔中位數 67.17 ms。CH2 第 11 秒的音仍在，第 12 秒預期起音後的 350 ms 為靜音，第 13 秒已恢復。操作者重聽正常與拔線片段後回報「只聽到停頓，沒聽到額外異音」。這項聽感適用於本次錄音的接回處。[波形比較](h-mtc-sd-20261121-211205/take3r-gap-audio-comparison.json) · [正常片段](h-mtc-sd-20261121-211205/take1-relock-listen.wav) · [拔線片段](h-mtc-sd-20261121-211205/take3r-relock-listen.wav) · [#1663](https://github.com/storytold/soundcraft/pull/1663)

追加的跨次相位與回送延遲分析另見[起音調查](h-mtc-sd-phase-20261121/REPORT.zh-TW.md)。

## #1663 的本體連續播放

沿用上述執行檔、SD 歌曲與 DIN 接線。Model 12 持續送出 30 fps non-drop。電腦在同一次播放中改變 Session Setup；下表的時間起算點為套用該段 session rate。[逐筆狀態與游標](round4-006a968-rate-soak.jsonl) · [分段統計](round4-006a968-rate-summary.json)

| Session rate | 播放時長 | 桌面版診斷 |
|---|---|---|
| 29.97 non-drop | 3 分鐘 | 10.121 秒首次觀測到警告。速差中位數 +1000 ppm，重新定位 5 次，失鎖 0 次。 |
| 25 | 30 秒 | 第一次查詢（7 ms）就有速率不符警告，116 次查詢都有警告。 |
| 30 | 5 分鐘 | 1,338 次查詢全部為 Locked，速率警告、重新定位及失鎖都為 0。 |

同一輪也驗了 P-D1、P-D2 的控制介面。在起始時碼 01:00:00:00、offset 為 0 時，收到本體從零起算的時碼，狀態為 Before session start，播放維持停止。將 offset 設成 +01:00:00:00 後開始跟播，incoming 仍顯示本體的絕對時碼；改回 0 後重返 Before session start。圖形介面的兩種擷取手勢及本體螢幕與電腦畫面逐格比對，均另列待測。

## 實體路線

- **主機輸出。** 已成功的接法為 SoundCraft → Model 12 一般 USB MIDI → 背面 DIN OUT → UM-ONE 標示 TO MIDI OUT 的插頭 → 獨立擷取。停住錄音機並關閉本體 MTC／Clock 輸出。可驗 F8、F1、完整 SysEx 及時序。
- **本體輸出。** SD 歌曲播放 → DIN OUT → UM-ONE → SoundCraft Reader／Follower。Model 12 USB 可繼續供應音訊。分次開啟 MTC、MIDI CLOCK/SPP。若 WinMM 拒絕兩個程式同時開同一埠，改以另一個經確認同步傳送的來源做獨立對照。
- **外部聲音。** Model 12 送 30 fps non-drop MTC、Clock 及 SPP；其 MIDI 表將輸入 Clock、quarter-frame、Position 列為不辨識。驗證 SoundCraft 輸出確實帶動外部節拍時，需要可跟 Clock 的獨立發聲端，將它和 SoundCraft click 錄入同一 ADC 時基的兩個分離聲道。S-MU2000 在過往專案是插件，可用於驗 SoundCraft 跟播。Model 12 當主機時可錄它自己的 metronome 與 SoundCraft click。[Model 12 手冊 pp.54、75](https://cf.tascam.com/wp-content/uploads/downloads/products/tascam/model_12/model-12_om_efs_vh3.pdf)

## §9A

| 案號 | 電腦腳本或介面操作 | 現場條件與證據 |
|---|---|---|
| R-1 | buffer 設 8192 或 driver 的最大可用值；停止 5 秒後 Play，Clock 20 次、MTC 10 次，最小化快捷鍵 5 次 | 接妥迴路。逐次 ≤1 秒收到首筆有效傳輸，timeout 增量 0；確認最小化時快捷鍵實際到達 |
| R-2 | 96 kHz 存 +20000，切 48 kHz 開關兩個對話框，再切回 | 請求 20000、生效 12000，返回 96 kHz 仍存 20000。另記裝置的實際取樣率 |
| R-3、R-4 | 0、−L/2、−2L 各播 30 秒，補償開、關各一次；120 ↔ 60 BPM 各五次 | 記實際 lead 和 wire。外部聲響須獨立接收端雙軌回錄。半 lead 差 ±1 ms；p95 ≤2 ms，受限抖動 <1 ms。每次改 tempo 一次 relocate，首拍差 <2 ms |
| R-5 | 120 BPM、48 kHz、256 frames，loop 0–1 小節，補償關，接近尾端停 20 次 | 每次 wire 上一次 Stop、無短暫 Start |
| R-7、R-8 | 同埠 Clock + MTC，記錄移除 USB 埠時的狀態列、診斷與恢復後首筆 | 需現場拔插實際 USB。可讓 UM-ONE 作輸出，保留 Model 12 音訊；另由獨立接收埠觀察。錯誤 ≤2 秒，撤除 Clock 後重連首筆 Stop，MTC 繼續，音訊訊息保留 |
| R-9 | 模擬 64 個目的地的 UI 回歸可自動跑；有大量真埠時在 1366×768 捲到底 | 本次列出 4 個 output（含 GS）。注明來源及 OK/Cancel 可見性 |
| P-D1、P-D2 | 比對收到的時碼，兩種擷取方式，提交前後、兩處 offset 設定及舊檔 | 本體定位與播停。顯示差 ≤1 frame、擷取 ≤2 frames，lock ≤1 秒；加 1h 時第 10 秒映至 01:00:10:00，received 保持 00:00:10:00，還原 offset 回到 Before session start |
| P-D3 | 30 ND 入，程式設 29.97 ND 播 3 分鐘、25 播 30 秒、30 播 5 分鐘 | 需夠長的歌。29.97 ND 在 30 秒內警告，+1000±100 ppm；記 relocate 次數。25 鎖即警告，30 全段無誤報 |
| P-D5 | click 路徑無高延遲插件、加入 ≥2048 samples 插件、關閉補償，各錄一次 | 需外部跟拍發聲端及兩軌共同取樣。比較相對差 ≤1 ms；關閉後 system delay 為 0 |
| P-D6 | 量晚 N samples，設定輸入 −N 重測；核對同名輸出設定與舊正值升級 | 本體 CLOCK/SPP 及 metronome。兩拍分軌後比較 ≤1 ms；同名輸出不變 |

R-6、R-10 至 R-13 由自動回歸覆蓋。USB 與 DIN 逐路留下原始資料。

### N-7 三次 Model 12 時碼中斷

每種模式先鎖定同一持續播放的來源，拔 **DIN 訊號線** 並保留 USB MIDI 與音訊端點。從最後有效 QF 對到 mtc_chase 和 transport 狀態時間。一般 100 ms UI 輪詢僅能粗估，精確停下時間須以 wire 及較高速的對照量測。

| 模式 | 本體操作 | 檢查 |
|---|---|---|
| None | 已鎖後拔 DIN、再插回 | 兩幀無有效 QF（30 fps 約 66.7 ms）即停止，無 coast。恢復重新定位、鎖定 |
| Frames = 8 | 拔超過 8 幀再接回；另補短於 8 幀的中斷 | 約 267 ms 後停止；短中斷若在容許範圍便直接回鎖。難以手動控制時以受控閘斷另列短中斷的結果 |
| Jam Sync | 已鎖後拔 DIN 至少 10 秒，再接回同相來源 | 位置持續推進，同相接回無跳動。另測來源跳一秒時，需兩組一致才重定位 |

## §9B

1. 實體迴路 Clock 120/180 BPM、歌頭／非網格起點、SPP/Continue 與首個 F8；對照 0 和 −200 samples。
2. MTC 23.976、24、25、29.97 ND、29.97 DF、30 fps。核對停止 full-frame、播放 QF 無 <1 ms 成對訊息、兩個 DF 邊界、預設一小時和埠校正。23.976/24 與 29.97 ND/30 各共用 wire rate code，還需量實際 QF 速率。
3. 同一埠發送 Clock + MTC，確認兩條流、同一校正與單一連線。
4. Recorder MTC 播停／定位、停超過 5 秒再 roll、首次和穩態偏差、漂移及長時 arrival_delay_p95_us、01:00:00:00 前後、N-7 三模式、session 切換、Online 拒絕錄音及起播切離 Online。歌曲長度不足時，另列以較近 session 起始點驗的等價邊界。
5. Recorder CLOCK/SPP 的 lock、BPM、改 tempo、已播小節、遺失／coast／stop。後退 SPP → 改主機 tempo → Continue 須確認本體確實送出 FA/FB/FC；手冊只承諾 Clock/SPP，缺少的訊息可由另一個來源經實體迴路注入，另列來源。
6. 1、2、4、5 各重做多插件小 buffer 與最小化情境。各附 diagnostics、實際 buffer、CPU／audio dropout、原始資料。

## 工具

用 python round4-preflight.py --output inventory.json 列舉埠與三個 checkout 的 commit。加 --port（既有測試控制埠）、--seconds、--interval 與 --case 可唯讀輪詢 setup.midi_sync_status 及 transport.status。輸出須用新的檔名。checkout 的 HEAD 需與執行中 binary 另行核對。

desktop_sync.py 提供私用桌面 RPC。monitor.py 會開多個 MIDI input 並 append 固定的 wire.jsonl，capture_mtc.py 預設固定來源，verify_wire.py 針對舊資料格式。正式測試應使用每次獨立的資料檔與明確指定的埠。phase_capture.py 與 measure_chase_revision.py 可回錄或離線比對 S-MU2000 既有 19 音，端點錄音和外部實際發聲的共同 ADC 量測分開留存。

### #1662 實體迴路

執行 `python round4_beat_wire.py --case r1` 可預覽計畫。`--case r5` 與 `--case grid` 分別對應迴圈結尾和 §9B.1。三組預覽均不開啟設備。

正式驗收請依序獨占 Model 12 與 UM-ONE。在上述命令加上 `--run --commit <40位完整SHA> --exe <對應的桌面執行檔>`。腳本會選預設音訊系統中唯一符合 Model 12 的輸出；若有多個，可用 `--audio-device "<完整名稱>"` 指定。程式核對實際音訊裝置與取樣率，將執行檔 SHA-256、每次獨立的封包時間、控制命令時間、診斷、實際 buffer 及結果記入新目錄 `round4-wire/<case>-<ns>`。MIDI 線路為 SoundCraft → Model 12 USB MIDI → Model 12 MIDI OUT → UM-ONE → 電腦。

- R1 需約 135 秒。最大 buffer 優先用 8192；若驅動支援的上限較低，記錄驅動上限後用 `--buffer` 指定。每次停止至少五秒，共 20 次，比對一秒內的 Start/F8 及診斷。用 `--case r1-min` 可另開專屬 SoundCraft 視窗，核對每次都在 Windows 最小化狀態後，用應用程式的 Space 快捷鍵路徑起播及停止五次。#1663 的十次 MTC 起播另外驗收。
- R5 需約一分鐘。在 256 frames、120 BPM、補償關閉的單小節迴圈中測 20 次。以接收的 Start 作起點，在預計結尾前 3 至 18 ms 送 Stop。核對 MIDI 端一個 Stop、接近 96 個脈衝、無重新起跑，以及 SoundCraft 的停點。若在送出 Stop 前已收到迴圈重新啟動，保留該次為無法判定並重測。
- §9B.1 需約半分鐘。120 和 180 BPM 分別從歌頭及第 47,125 個 sample 開始，各跑一次 0 與 −200 samples。核對 SPP 數值、Continue／Start 至第一個 F8 的間隔、24 PPQN 速率及最後 Stop。接收時間與呼叫 Play 的時間之差包含 Windows 排程和驅動延遲；精準量出音訊對 MIDI 的 −4.167 ms 必須另加同步音訊參考。
- 可選 `--case phase` 需約 15 秒，120、180 BPM 各持續播放一次，依序設定 0、−200、0 samples。用兩段零校正的 wire clock 相位內插為同一次播放的基準，計算中段提前量、Windows 接收時間的 P10 至 P90 幅度與實際校正上限。輸出的 pass 表示已取得三段播放中的封包，定量結論應引用 receiver_advance_ms 及 receiver_minus_diagnostics_ms。

### 2026-11-20 Windows 實體迴路結果

測試版本為 #1662 的 `02e63c602d31bd6c53ade0ae3fe487cd994ac5e5`，桌面執行檔 SHA-256 為 `7d90e6c3ffd178ff5c8e7a0d197262030581167a33ff5eabc98b5d11722a7f0c`。SoundCraft 從 Model 12 一般 USB MIDI 埠送出，UM-ONE 從 Model 12 實體 DIN OUT 收回。音訊使用 WASAPI 標準桌面版的「喇叭 (Model 12)」，48 kHz、雙聲道、F32。用程式實際挑選裝置設定的函式讀回，此格式的最小及最大值均為 480 frames。另嘗試 20 個 buffer size，只有 480 開成指定值。[實際裝置格式](../r4-model12-exact-buffer.log) · [各次開啟結果](round4-wire/buffer-probe-1795185409831140100/sizes.json)

| 項目 | 實機結果 | 證據 |
|---|---|---|
| R1，最大可用 buffer | 停止至少五秒後起播 20/20 次成功。呼叫 Play 到外部收到首個 F8 為 56.1–81.0 ms，中位數 61.1 ms；各次均收到 Start、時鐘與 Stop，sent 遞增，timeout 持續為 0。 | [摘要與逐次診斷](round4-wire/r1-1795185812750224300/summary.json) |
| R5，單小節停止 | 120 BPM、補償關、480 frames。在距預期結尾 28–60 ms 送 Stop，20/20 次接收端只有一次 Start／Stop，收到 94–96 個 F8，SoundCraft 停於 sample 92,160–95,040（小節尾為 96,000）。原條件 256 frames 需另一個接受該格式的音訊後端。 | [摘要與逐次診斷](round4-wire/r5-1795185756428805700/summary.json) |
| §9B.1，起點與校正 | 120／180 BPM、起點 0／47,125 samples、offset 0／−200 的八個組合均通過。歌頭收到 Start，非網格處收到正確 SPP 和 Continue。第一個 F8 到達時間符合下一個格點；零 timeout。 | [八個組合與原始時間戳](round4-wire/grid-1795185728308234900/summary.json) |
| §9B.1，同一次播放改校正 | −200 samples 換算為 −4.167 ms；外部 120 BPM 量到 −4.521 ms，180 BPM 量到 −4.128 ms。每段 F8 接收相位 P10 至 P90 的幅度介於 0.967–1.545 ms。 | [連續時鐘資料與相位](round4-wire/phase-1795185986048401200/summary.json) |
| R1，視窗最小化、Space | 五次均確認 Windows 主視窗為最小化，再經 SoundCraft 的應用程式快捷鍵路徑送入 Space。5/5 在 495–500 ms 內收到首 F8，Start／Stop 順序均正確。舊版 timeout 有兩次在前次 Stop 與下一次 Play 之間累加，只有 1/5 同時符合「累計為 0」。 | [逐次控制與診斷](round4-wire/r1-min-1795185945311377700/summary.json) |

前一版 `9056d90` 的邊界探測另行保留。於接收端預期繞回前 3–6 ms 才送 Stop，四次見到額外繞回；其中兩次外部已收到繞回的 Stop，但主機的 Stop RPC 仍未返回。48 kHz／480 frames 的單次 callback 已有 10 ms，此組不足以斷定 Stop 命令已在渲染繞回前處理。另一次非網格起播，線上封包正確但 timeout 增加 1；在可控制的 worker 排程中獨立重現，將比較基線移到送音訊命令之前後，已發布的轉換診斷為 0。[邊界探測](round4-wire/r5-1795185516291753600/summary.json) · [確定性重現](../r4-already-published-red.log) · [修正後回歸](../r4-already-published-final-suite.log)


### 修正 timeout 後的 Model 12 複測

實測執行檔建自 `ed28af4bd304769acf6ac62a7a2d9afdd0b153d3`，SHA-256 為 `8e818fb2f59ec32ef6d9e7fe577a02b5f3847549b59e21f44f7740cec44dd64b`。其後 `97d8cd0` 只修改 Rust 測試資料的發布方式。實機沿用同一個 48 kHz、480-frame 音訊格式與 MIDI 迴路。[建置紀錄](../r4-beat-desktop-ed28af4/build.json)

| 條件 | 實機觀察 |
|---|---|
| 連續 20 次各停止至少五秒再起播 | 20/20 次依序收到 FA、F8、FC，呼叫 Play 至首 F8 為 57.4–82.8 ms，中位數 67.4 ms。各輪 timeout 都為 0。[20 輪封包與診斷](round4-wire/r1-1795186543686263900/summary.json) |
| 視窗最小化時從應用程式 Space 快捷鍵起播 | 5/5 次收到 FA、F8、FC，首個 F8 用時 491–500 ms，timeout 全程為 0。[五輪封包與診斷](round4-wire/r1-min-1795186397224079200/summary.json) |
| 迴圈結尾停止 | 20/20 次各收到一個 FA、一個 FC 和 94–96 個 F8。每次在預期結尾前 28–60 ms 送出 Stop，SoundCraft 均停於 sample 92,160–95,040。[20 輪封包與停點](round4-wire/r5-1795186467714571300/summary.json) |
| 持續播放中改校正 | 0 → −200 → 0 samples。相對前後兩段未校正時鐘，120 BPM 的中段提前 4.268 ms，180 BPM 提前 4.071 ms，預期提前 4.167 ms。各時間窗線上相位 P10 至 P90 幅度為 0.785–1.117 ms。[兩種速度的連續 wire 相位](round4-wire/phase-1795186523820810100/summary.json) |

首次八組網格測試有 7 組通過。首組 Play 前診斷為 connected=false，約 204 ms 後外部收到 SPP=2、Continue，隨後收到 F8。因此該次量到的是輸出端點在播放中連上後的同步。後續八組逐一讀回 connected=true 才送 Play，8/8 均依起點收到正確 FA 或 SPP/FB。歌頭首 F8 距 FA 為 0.249–0.317 ms，sample 47,125 的首 F8 距 FB 為 17.691–19.076 ms；timeout 全程為 0。[開埠後的八組複測](round4-wire/grid-1795186676580140200/summary.json) · [首次八組的連線狀態及時間戳](round4-wire/grid-1795186440044278800/summary.json)

### R3 補償與提前上限

取當時 WASAPI 的回報 lead 換算為 samples，依次設為 0、負半倍或負兩倍、再回 0。在同一段不中斷播放的 20 BPM 時鐘，以前後兩段零校正內插出基準。每個區段使用 24 個 F8；相鄰 F8 為 125 ms，可分辨約 47 ms 的位移方向。此靜音專案的 mixer system delay 為 0。[四組原始封包、逐段診斷與相位](round4-wire/r3-1795186704939160000/summary.json)

| 補償 | 校正／裝置 lead | 要求 samples | 診斷 advance_limited | 診斷總位移 | 預期相位變化 | 接收端量到 |
|---|---:|---:|---|---:|---:|---:|
| 開 | −0.5 倍 | −1126 | false | +23.479 ms | −23.458 ms | −23.275 ms |
| 開 | −2 倍 | −4508 | true | +1.000 ms | −45.937 ms | −45.574 ms |
| 關 | −0.5 倍 | −1103 | true | 0 ms | 0 ms | +0.074 ms |
| 關 | −2 倍 | −4412 | true | 0 ms | 0 ms | +0.337 ms |

四組的要求值、有效總位移與上限旗標均符合預期；DIN 收包相位與預期之差介於 +0.074 至 +0.364 ms。與音訊瞬態的相對相位仍需同步錄音測量。

### R1 併發回歸測試

音訊 callback 在發布位置時若遇到鎖競爭，會略過當次更新。測試刻意持有鎖並只嘗試發布一次，可確定重現第一個 180 ms 案例漏收 FA。新的 fixture 在一秒上限內取得 timeline，直接核對唯一一次成功發布的 pass 與播放狀態，再檢查同一個 worker、同一次喚醒能否送出 FA 與 F8。50 次靜止 callback 仍經正常發布路徑，各次均不增加 worker 輪詢次數。播放套件串行 142 項通過、2 項忽略，另以 8 緒連跑三輪皆相同。[受控失敗](../r4-publication-fixture-red.log) · [串行結果](../r4-publication-fixture-suite.log) · [第三輪併發結果](../r4-publication-fixture-parallel-3.log)

## #1669 Model 12 外部 MIDI Clock 跟播與倒退定位

2026-11-20 於 Windows 使用 `104a9fc` 桌面程式，SHA-256 為 `60D1F4F74EBBC98E190895247A5DC84C783D0520418D25E3F8E68E7FD15C5390`。Model 12 本體錄音機提供時間基準，SoundCraft 選取 Roland UM‑ONE，輸入校正為 0 samples、失碼策略為 coast。同一台電腦並行記錄 Model 12 USB MIDI 與經 UM‑ONE 的 DIN MIDI，另從 SoundCraft 擷取 transport 與 follow 診斷。

| 量測 | 第一次播放 | 往回定位後第二次播放 |
|---|---:|---:|
| 本體傳輸 | Start → Stop | 倒退 SPP 88 → 41，再 Continue → Stop |
| 兩路 MIDI 實測中位速度 | 120.00 BPM | 120.00 BPM |
| SoundCraft 鎖定期間的中位估速 | 120.008 BPM | 120.009 BPM |

兩路各收到 842 個 F8、1 個 FA、1 個 FB、2 個 FC。兩次操作期間各有 4 個 F2，依序為 0、88、41、93（單位為十六分音符）。第二次按停約 79.23 秒後，又記錄到 F2=0，因此完整檔案中每路各有 5 個 F2。SoundCraft 在兩次播放均進入 Locked，兩次停止後均顯示 Stopped。操作員確認兩輪均維持同一個速度。倒退定位前後改變主機 tempo 的案例目前只有回歸測試；P-D6 的聲音相位仍需兩路同錄。這次資料可查閱 [原始 JSONL](round4-104a9fc-clock.jsonl) 及[分段統計](round4-104a9fc-clock.out)。

### #1669 腳本改速與實體 MIDI 迴路

固定執行檔 `104a9fc` 使用獨立的 48 kHz 靜音專案。PC 腳本先送出 SPP=0、Start 與 120 BPM，刻意停送 Clock 1.1 秒，再送 Stop、倒退的 SPP=12、停止中的 100 BPM Clock、Continue 及最後的 Stop。實體路徑為 Model 12 USB MIDI → Model 12 MIDI OUT → UM‑ONE DIN → 電腦。這輪由 PC 產生速度變化；前一節由 Model 12 本體產生時鐘。

| 失碼策略 | 停鐘時的 SoundCraft 狀態 | SoundCraft 鎖定中位 BPM（前 → 後） | 倒退定位 | 通過 |
|---|---|---|---|---|
| Coast | Coasting，繼續播放 | 120.015 → 100.000 | 72,000 samples | 8/8 |
| Stop on loss | Stopped，停止播放 | 120.005 → 100.002 | 72,000 samples | 8/8 |

每輪 UM‑ONE 都收到 315 個 F8、2 個 F2、1 個 FA、1 個 FB 及 2 個 FC。停止期間的 49 個 100 BPM Clock 沒有觸發播放，FB 送達後兩輪均重新鎖定，最後 FC 後均停止。原始 host 與 wire 紀錄及八項判定見[本輪摘要](round4-follow-loop-1795184632076061100/loop/summary.json)。同時錄下兩聲源的 P-D6 輸入校正尚待測量。

## MTC 輸出封包與可判定範圍

#1663 的 `006a968` 將 MTC 經 Model 12 USB MIDI 送往 DIN OUT，由 UM‑ONE 回收。六種 session rate 合計 72/72 項輸出檢查通過。29.97 DF 跨一般分鐘從 `00:00:59;29` 跳到 `00:01:00;02`，跨第十分鐘則從 `00:09:59;29` 接到 `00:10:00;00`。同一埠的 offset 增加 5 ms 時，接收端分別量到 MTC 延後 5.234 ms、Beat Clock 延後 4.951 ms。這些是 MIDI 收包時間。短時間的封包計數本身無法獨立區分兩種共用 rate code、速率只差 0.1% 的格式。

在 30 fps 且視窗最小化時，Python 接收器曾出現一次 QF 缺號。改用獨立的 WinMM 原生收包器重做五輪，共 1,891 個 QF，五輪均無缺號，最短相鄰間隔為 4–5 ms。原異常無法據此歸因於單一元件。[獨立收包器、每輪判定與診斷](round4-006a968-mtc-wire-20261120-224732/wire-analysis.json)

三次 N-7 拔線使用 Model 12 的五針 **MIDI OUT**。R-7／R-8 所要求的 Windows USB 端點消失、播放中移除輸出後再恢復，仍待獨立實機測試。設備兩項發碼均已關閉。程式的時間戳及實體 MIDI 迴路不能替代兩路同步聲音量測。R-3／R-4 與 P-D5／P-D6 的聲學相位門檻，以及大量外掛的小 buffer 組合，目前保留待驗。
## 本機 Windows 驗證

- #1662 最終功能分支 `97d8cd0` 的播放測試串行及三輪 8 執行緒均有 142 項通過、2 項略過。加入 #1536、#1658 的本機整合 `585cc1a` 通過格式與 workspace/all-targets 嚴格 Clippy。Engine 435、Playback 142、UI 352，合計 929 項通過、0 項失敗、2 項略過。[完整整合日誌](../../tmp/r4-beat-win-97d8.log)
- #1662 原分支三庫另跑一次，播放 142、UI 352 通過；Engine 434 通過，唯一失敗為 Windows 影片重新連結。在上述本機整合中相同測試已通過。[原分支完整三庫日誌](../../tmp/r4-raw-97d8-libs.log)
- #1663 功能分支 `ee80920` 的播放／UI 為 176／372 項通過。Engine 445 項通過，1 項既有 Windows 影片重新連結測試失敗。含 Windows 前置修正的本機整合 `ef7feaf` 通過格式與嚴格 Clippy，三個庫合計 994 項通過、0 項失敗、3 項略過。[驗證摘要](../r4-win-mtc-gate-ee80920/result.json)
- #1669 原分支的播放、UI、Engine 分別通過 188、383、446 項，僅上述影片重新連結測試失敗。整合 0a8f553 的七項本機 CI 全數通過，含嚴格 Clippy、文件測試、WebAssembly；2,040 項通過、5 項略過。[完整 CI 日誌](../follow-r4-0a8f553-integration.log)
### 最終 #1669 版本的實體迴路複測

#1669 的原始版本為 `2aa39ff`。本輪使用同一版本與 Windows 修正 #1536、#1658 的整合執行檔 `0a8f553`，SHA-256 `f02d245af33e29ca3389f2e6cb9dfb1f293fb1e7745cd14ac4e69b41def88f83`。兩份程式的時鐘、播放及 UI 原始檔相同。腳本透過 Model 12 USB → DIN OUT → Roland UM-ONE 送入訊號，UM-ONE 同時保留獨立 MIDI 封包紀錄。

| 失碼策略 | SoundCraft 鎖定中位 BPM（前 → 後） | DIN 中位 BPM（前 → 後） | SPP=12 | 通過 |
|---|---|---|---|---|
| Coast | 120.006 → 100.004 | 120.00 → 100.00 | 72,000 samples | 8/8 |
| Stop on loss | 119.996 → 99.998 | 120.00 → 100.00 | 72,000 samples | 8/8 |

每種策略都收到 315 個 F8、2 個 F2、1 個 FA、1 個 FB、2 個 FC。刻意停鐘 1.1 秒時，兩個策略分別繼續與停止播放。倒退定位後的 49 個時鐘維持停止，Continue 恢復播放，最後 Stop 結束播放。設備已釋放。[原始資料與判定](round4-follow-loop-0a8f553-1795188051443765400/loop/summary.json)


### 副歌重來一次（#1669，實機待驗）

2026-11-20 使用 Windows 整合版 `0a8f553`。八小節伴奏採 120 BPM、4/4、48 kHz。低音由 S‑MU2000 即時演奏，銅鈸與三組鼓聲取樣自同一音源，由 MIDI 音符觸發。第 5 小節第一拍只安排一個銅鈸，便於從回錄辨識副歌起點。[伴奏專案](chorus-rehearsal-1795189811276/Back%20to%20the%20Chorus.scraft)

本機從頭播放時，Model 12 的 Windows 音訊輸出回錄捕捉到一次銅鈸，與第一個低音起音相隔 384,000 個取樣（8.000 秒）。五軌均解除靜音，Windows 預設多媒體輸出也已解除靜音。操作者回報聽不到聲音；查詢當下 SoundCraft 顯示外部 MIDI Clock 等待中，沒有 BPM 讀值。另向同一個 Windows 音訊輸出直接送出兩次短伴奏，供獨立檢查實體監聽。[本機回錄](chorus-rehearsal-1795189811276/reference.wav) · [銅鈸比對結果](chorus-rehearsal-1795189811276/reference-analysis.json)

待確認本體監聽，並擷取 Model 12 在第 8 秒送出的 SPP（預期 64）、Continue 和伴奏起音。此段的 8.000 秒為本機從頭播放的對照值，實機從副歌重來的時間誤差仍待量測。

2026-11-21 操作者確認，電腦直接播放兩遍時，本體 MAIN L/R 電平表未動，也未聽到伴奏。該測試繞過外部時鐘。接著檢查本體 USB AUDIO 的 PC CH1/2 回放目的地。

第二次監聽診斷：本體 MAIN 推桿在 0 dB。直接播放時，操作者確認 PC RETURN 第 1、2 路電平都沒有跳動，未聽到鼓聲。Windows 列出正常啟用的 Model 12 USB 音訊裝置，喇叭端點預設格式為雙聲道 24-bit、48 kHz，TASCAM 儲存的 ASIO 取樣率也為 48 kHz。需再核對目前本體歌曲的取樣率。

操作者隨後確認目前歌曲為 44/16（44.1 kHz、16-bit），與當時 48 kHz 的 Windows 播放與錄音端點不同。已停止驗收專案的播放，暫時釋放 Model 12 的 WASAPI 輸出，供原廠 ASIO 驅動進行獨立診斷。首次使用阻塞寫入逾時；釋放 SoundCraft 的輸出並改用回呼後，44.1 kHz 的 ASIO 靜音測試完整處理 44,100 個音框。仍待確認本體 PC RETURN 的實體電平；此處尚未驗證從第 8 秒再起播。

44.1 kHz 原廠 ASIO 音樂輸出 1/2：完整處理 220,500 個音框（5 秒），操作者看見 PC RETURN 有電平但喇叭無聲。CH1、CH2 保留 LIVE 給麥克風及 PC1X。本結果確認 USB 回放抵達本體。另以全靜音驗證 ASIO 輸出 9/10 可開流，實際監聽及外部第 8 秒起播仍待驗。

9/10 監聽已由操作者確認：Model 12 的 CH9/10 空閒，設為 PC 並分配至 MAIN，44.1 kHz ASIO 9/10 送出的五秒片段可從接在 MAIN OUTPUT L/R 的喇叭聽見。CH1 麥克風、CH2 PC1X 均可保留 LIVE。其後另以本機監聽轉送程式將 #1669 即時專案播放的雙聲道 WASAPI 輸出轉到 ASIO 9/10（44.1 kHz）。12 秒對照回錄辨認到一次副歌銅鈸，監聽轉送期間有非零訊號。此轉送屬本機測試配置；回錄取自轉送前，尚未量測喇叭端的實際延遲。[即時對照回錄比對](chorus-rehearsal-1795189811276/monitor-reference-analysis.json)

停止中第一次從 Model 12 定位：操作者確認 120 BPM、4/4，本體秒數顯示 8。SoundCraft transport.status 回報 playing=false、position=390000，專案為 48,000 Hz，實際游標 8.125 秒；第 5 小節起點為 384000（8.000 秒），差 6000 samples＝一個十六分音符。尚待核對該次 MIDI F2 原始值，未算作準點重播。

停止中第二次直接定位：操作者先回歌頭再重新確認 00h00m08s，回報尚未播放。在此次監看區間，USB 與 UM-ONE 兩個輸入均已成功開啟，兩路均未錄到新的 F2；主機仍停止在 390,000 samples（8.125 秒）。此輪不能把游標值歸因為本體送出 SPP=65；需比對下一次按播放時的封包及銅鈸起音。[雙路 MIDI 紀錄](chorus-rehearsal-1795189811276/locate-8-live.jsonl)

#### 副歌重來一次：實機結果與定位對照（2026-11-21）

**直接從第 8 秒重播的第一拍尚未通過。** 操作者從 Model 12 按播放，聽到開頭有銅鈸聲。以下判定檢查的是專案中排在 8.000 秒的那一下特定銅鈸起音。從歌頭播放可以辨認一次，與原始樣本的正規化波形相關係數約 1.000；辨認門檻為 0.90。從頭播放時，第一個低音與該銅鈸相隔 384,000 個取樣。

| 操作 | 起播前的位置 | 副歌第一拍在回錄中的結果 |
|---|---:|---|
| Model 12 本體顯示 8 秒，按 ▶ | USB 和 DIN 的完整記錄均為 SPP 65，游標 390,000 samples（8.125 秒）；按 ▶ 收到 Continue，之後收到 Stop | 未辨認到指定起音（最高相關 0.212）。操作者主觀聽到開頭有銅鈸；資料不足以確認聽到的是哪個聲音。 |
| 電腦送精確位置，經 Model 12 USB → MIDI OUT → UM-ONE | SPP 64，游標 384,000 samples（8.000 秒），Continue | 同樣未辨認到指定起音（最高相關 0.224），後段有伴奏。此結果表示只修正定位一格仍不足以通過；首事件、取樣器與跟播排程的原因尚待隔離。 |
| 同一實體迴路送提前一拍的位置 | SPP 60，游標 360,000 samples（7.500 秒），Continue | 辨認到一次銅鈸（相關 0.99998）；依電腦回錄與 UM-ONE 時鐘估算，起音比預期第 24 個脈衝間隔的落點早約 5.4 ms。這是轉送到 ASIO 喇叭前的估值。 |

第一次本體定位的完整封包在按 Stop 後寫入檔案，兩路起播前最後的 F2 均為十六進位 F2 41 00（65）；第二次停止中重新定位未觀察到新 F2。兩次電腦對照只替代發碼端；沿用同一專案、相同聆聽及數位回錄路徑。本輪未量測喇叭端聲學延遲。排練時可用一拍預備再進副歌。

[本體起播資料](chorus-rehearsal-1795189811276/chorus-from-8-analysis.json) · [本體回錄](chorus-rehearsal-1795189811276/chorus-from-8.wav) · [精確第 8 秒](chorus-rehearsal-1795189811276/precise-64-analysis.json) · [提前一拍](chorus-rehearsal-1795189811276/lead-in-60-analysis.json) · [開頭波形分段比對](chorus-rehearsal-1795189811276/first-second-comparison.json)

### 外部 MIDI Clock 從副歌續播（#1674，2026-11-21）

舊版 #1669 在精確的 8.000 秒定位仍會漏掉銅鈸。共用的外部時鐘播放流程將收到第一個脈衝時的經過時間及裝置延遲計入音訊游標，原本 MIDI 音符排程也從該游標才開始搜尋。修正保留時鐘補償，另將指令要求的音樂起點交給第一個有效音訊區塊。這適用於使用外部 MIDI Clock 驅動 SoundCraft 專案內樂器的工作流程。Model 12、UM-ONE 和 S-MU2000 為本次驗證設備與音源。

電腦發送 Song Position Pointer → Continue → 144 個 Clock（目標 120 BPM）→ Stop，經 Model 12 的 USB MIDI 與背面 DIN OUT、UM-ONE 回到 SoundCraft。每輪均先讀回停止位置並獨立擷取 DIN 封包。相同的八小節專案在 48 kHz 擷取數位輸出，另經 44.1 kHz ASIO 9/10 送回 Model 12，在 USB 11/12 回錄 MAIN。以正規化波形相關係數 > 0.90 辨識同一個銅鈸樣本，另用從歌頭播放的錄音核對後段伴奏。此次精確定位由電腦發碼，本體手動定位結果見前節。

| 起播方式 | 數位回錄的銅鈸次數 | MAIN 回錄的銅鈸次數 | 判讀 |
|---|---:|---:|---|
| 本機從歌頭播放 | 1 | 1 | 確認兩條錄音路徑可辨認目標銅鈸 |
| SPP 64，8.000 秒，兩輪 | 1、1 | 1、1 | 銅鈸在兩輪都是第一個可辨識起音，計數涵蓋 Stop 後的回錄 |
| SPP 65，8.125 秒，兩輪 | 0、0 | 0、0 | 後段伴奏與對照相關 0.998、0.998，確認續播正常且未補敲 |
| SPP 60，7.500 秒，提前一拍 | 1 | 1 | 連續跟播跨過副歌仍只敲一次 |

**兩種時間應分別讀取。** 在精確定位的兩輪，銅鈸與數位回錄中的第一個可聽起音相差 0.0 ms。相對於 UM-ONE 收到的第一個 Clock，電腦數位回錄的估計落後 40.25、46.82 ms；含監聽轉送的 MAIN 回錄落後 117.34、123.63 ms。提前一拍的對照則分別為 −7.68 與 +68.78 ms。這些是此次 Windows 擷取路徑、設備與緩衝設定的測值；未量測喇叭聲學輸出。本次證實起點事件不漏、不重複，現場端到端仍有可測延遲。

實機使用 Windows 整合基底 `0a8f553`（含 #1536、#1658）加上本次修正，執行檔 SHA-256 `7503e25deebb9bb0cdab6bd7eaf323f433456add658158e578fa64a0ec0b0155`。原專案 SHA-256 `992c9ea2e252052261f326a03be545683f3bf9a59d1db5ab166a0acc1d5a7071`。

[原始封包與兩路 WAV 所在目錄](chorus-continue-1674/) · [波形與時序量測](chorus-continue-1674/results.json) · [缺陷 #1674](https://github.com/storytold/soundcraft/issues/1674) · [原 PR #1669](https://github.com/storytold/soundcraft/pull/1669)


修正提交 `baab55e` 已推回 #1669。原分支的回歸測試先紅後綠；格式檢查通過，混音 100、播放 188、介面 383 項通過。引擎 446 項通過、1 項 Windows 影片重新連結失敗（#1536）。含 Windows 相依修正的整合版重新編譯後，引擎 447、混音 100、播放 188、介面 383，共 1,118 項通過、5 項依設定略過。四個 crate 的 all-targets Clippy（`-D warnings`）通過。GitHub 的 CI、Nix、SonarCloud 三項均為 `action_required`。

[舊版失敗紀錄](chorus-continue-1674/regression-before.log) · [原分支測試](chorus-continue-1674/regression-pr.log) · [整合版測試](chorus-continue-1674/regression-windows.log) · [整合版 Clippy](chorus-continue-1674/clippy-windows.log)



### 外部 MIDI Clock 起播延遲與監聽轉送（#1675）

沿用上一節的八小節 S-MU2000 伴奏、Model 12 USB MIDI → DIN OUT → UM-ONE、120 BPM、數位回錄 48 kHz、監聽 ASIO 9/10 與 MAIN USB 11/12 回錄 44.1 kHz。基準為 #1669 修好起點漏音後的 `baab55e`。修正前後各四次從精確的 SPP 64 續播。以讀入第一個 F8 為基準，臨時診斷版在接收、主機處理、專案準備、音訊回呼和第一個區塊混完時記錄時間；校對 UM-ONE 的獨立軟體擷取，兩者觀測同一個外部 Clock。雙路校時與 WAV 使用同一台 Windows 電腦的時鐘，毫秒值包含回呼時間估算。音符辨識沿用相關係數 0.90。

| 量測階段（毫秒）| 修正前，四輪範圍 | 修正後，四輪範圍 |
|---|---:|---:|
| MIDI 接收到主機處理 | 14.5–15.0 | 14.7–31.2 |
| 主機準備專案 | 7.404–7.565 | 0.001–0.002 |
| 播放指令到音訊回呼收到 | 2.9–9.6 | 1.0–7.4 |
| 回呼收到到第一個混音區塊完成 | 2.1–2.8 | 2.1–2.8 |
| MIDI 接收到區塊混完 | 27.6–34.9 | 18.5–34.6 |
| 混完到電腦數位回錄 | 12.4–13.0 | 11.8–14.6 |
| 第一個 Clock 到電腦回錄，平均（範圍） | 43.8（40.3–47.9） | 37.9（31.9–47.2） |

修正讓播放器在文件身分和已送出的速度圖相同時沿用已準備的專案。軌道編輯與尚未送出的速度變更仍會觸發更新。修正前後的端到端平均差 5.9 毫秒；修正後仍有一次主機派送等了 31.2 毫秒。此處能直接歸因的是省去了重複準備，無法從四輪推論所有裝置上的最低延遲。

**MAIN 多出的時間。** 最終版不含臨時時間探針。暖機後只改測試用監聽轉送的軟體佇列，依序做 20、40、60、60、40、20 毫秒，維持相同取樣率、ASIO 緩衝與音量。下表每欄列出兩次實測。逐次以同一個銅鈸波形比對；兩個獨立數位擷取程式的回呼時間戳有約數毫秒的差異，數位到 MAIN 的總數已包含此差異。

| 轉送預填 | 轉送程式收到波形到 ASIO 輸出回呼 | ASIO 輸出回呼到 MAIN USB 回錄 | 電腦數位回錄到 MAIN |
|---|---:|---:|---:|
| 20 ms | 32.5 / 28.5 ms | 14.5 / 14.5 ms | 45.1 / 41.1 ms |
| 40 ms | 45.5 / 46.8 ms | 15.5 / 15.5 ms | 59.3 / 60.3 ms |
| 60 ms | 68.9 / 62.0 ms | 15.4 / 14.5 ms | 82.3 / 74.5 ms |

早先兩輪多出 77.09 與 76.81 ms，當時只錄兩個端點。本輪的實測解釋了同量級的延遲如何形成，無法追溯先前每個中繼點的確切毫秒數。ASIO 回呼到 MAIN 包含輸出與回錄，不等於 Model 12 本體的單向延遲。前一組未加暖機的探索性 20 ms 首輪，多出 145.9 ms，其中觀察到軟體佇列等待 121.7 ms；記錄一併保留。喇叭的聲學輸出未量測。

未加探針的最終執行檔 SHA-256 `0442d8a4e8799cf45a65ad22223867abf634f678bebf19e10defc78fb92b42f0`，原曲 SHA-256 `992c9ea2e252052261f326a03be545683f3bf9a59d1db5ab166a0acc1d5a7071`。6 次 8.000 秒都有一個銅鈸，2 次 8.125 秒均為零，數位與 MAIN 兩路一致。相同音樂片段的後續伴奏另以波形確認。每輪 UM-ONE 收到 144 個 Clock。

原 PR 分支的回歸測試先在舊流程報「Continue rebuilt an unchanged session」，修正後混音 100、播放 189、介面 383，共 672 項通過、5 項略過。格式與 Windows 整合版兩個修改 crate 的嚴格 all-targets Clippy 通過。臨時分段探針與監聽程式均留在本機。

![修正前後延遲與監聽佇列對照](chorus-latency-1675-fixed/midi-clock-resume-latency.png)

![副歌起點與跨過起點時的實錄波形](chorus-latency-1675-fixed/midi-clock-resume-boundary.png)

[基準分段數據](chorus-latency-1674/split.json) · [修正後分段數據](chorus-latency-1675-fixed/split.json) · [未暖機探索紀錄](chorus-latency-1675-queue/split.json) · [最終版暖機對照](chorus-latency-1675-final/split.json) · [缺陷 #1675](https://github.com/storytold/soundcraft/issues/1675) · [原 PR #1669](https://github.com/storytold/soundcraft/pull/1669)

[逐次起音辨識結果](chorus-latency-1675-final/final-acceptance.json) · [修正前回歸失敗紀錄](chorus-latency-1675-fixed/lat-red.log) · [完整測試結果](chorus-latency-1675-fixed/lat-final-tests.log) · [Windows Clippy](chorus-latency-1675-fixed/lat-clippy.log)

### 第一個 MIDI Clock 到播放命令的等待

上一輪那次 31.188 毫秒是從第一個 Clock 到主機處理 Play 的時間。該次沒有作業系統排程或逐幀紀錄。本次以同一份伴奏在舊版 `f5de549` 重測八次。喚醒呼叫在 0.001–0.514 ms 內返回，主機進入介面更新時已過 14.391–15.349 ms，進入更新後到處理 Play 只花 0.012–0.043 ms。這八次沒有重現 31.188 ms 的極值，但確認即使已完成定位，舊版仍要等下一個介面更新才能派送。

修正後，在停止且定位完成時準備一次起播。選定的輸入收到 Continue 後的第一個 Clock，即可直接派送同一個播放命令。介面接著接收結果；改過專案或定位尚未就緒會走原本的處理流程。埠校正量和裝置輸出提前量仍計入播放位置。

| 自收到第一個 Clock 起算 | 修正前 | 修正後 |
|---|---:|---:|
| 播放命令（8 次範圍） | 14.427–15.367 ms | 0.001–0.002 ms |
| 數位回錄銅鈸（6 次平均與範圍） | 35.2 ms（32.8–39.5） | 21.3 ms（16.0–25.0） |
| 拿掉探針後的數位銅鈸 | — | 19.5 ms（15.3–25.2） |

前版探針在送出播放命令前取樣，修正版於送出返回後取樣，軟體時間戳解析度為微秒。移除探針的最終版也涵蓋快速連續定位時發布最新速度表的處理。三輪各測 6 次 SPP 64（8.000 秒）、2 次 SPP 65（8.125 秒），每次皆收到 Continue、144 個 Clock 與 Stop。使用同一份八小節 S-MU2000 伴奏、120 BPM、Model 12 USB MIDI → 實體 DIN OUT → UM-ONE，數位與 MAIN USB 兩路分別以 48 和 44.1 kHz 回錄。三輪每次 8.000 秒皆辨識到銅鈸一次、8.125 秒皆為零；後續伴奏各次皆通過波形比對。以第一個 Clock 為起點，Model 12 MAIN USB 回錄的六次平均，舊版為 92.6 ms (90.3–97.0)，移除探針後為 77.6 ms (74.5–82.9)。喇叭的聲學延遲未列入量測。

![第一個 Clock 到派送播放與數位回錄的比較](chorus-dispatch-final/midi-clock-resume-dispatch.png)

[舊版逐次量測](chorus-dispatch-before/final-acceptance.json) · [修正版逐次量測](chorus-dispatch-final/final-acceptance.json) · [移除探針的逐次量測](chorus-dispatch-release/final-acceptance.json) · [統計與重繪程式](chorus-dispatch-final/plot_dispatch.py)

[舊版回歸失敗](chorus-dispatch-final/dispatch-red.log) · [修正版回歸通過](chorus-dispatch-final/dispatch-green.log) · [原分支四庫結果，含既有 Windows 影片重新連結失敗](chorus-dispatch-final/dispatch-raw-suite.log) · [Windows 整合版四庫 1120 項通過、5 項略過](chorus-dispatch-final/dispatch-integrated-suite.log) · [聚焦回歸連跑 12 次](chorus-dispatch-final/dispatch-repeat.log) · [Windows Clippy](chorus-dispatch-final/dispatch-clippy.log)


### 數位回錄到 Model 12 MAIN 的 58.14 毫秒

以同一份八小節 S-MU2000 伴奏與 `8ca7cbf` 對應的 Windows 整合測試版，重測外部 MIDI Clock 續播。Model 12 USB MIDI → DIN OUT → UM-ONE，120 BPM，每次 144 個 Clock。SoundCraft 仍輸出至 48 kHz 的 S/PDIF 端點。測試用監聽程式從該端點擷取音訊，轉為 44.1 kHz 經 ASIO 9/10 播放，再從 MAIN USB 11/12 回錄。兩個版本識別值與前輪相同。[執行檔與伴奏 SHA-256](chorus-main-return-split/control.json)

| 平均時間（ms） | 前輪原始設定，6 次 | 本輪預填 40 ms，4 次 | 本輪預填 20 ms，4 次 |
|---|---:|---:|---:|
| 首個 Clock 到電腦數位回錄 | 19.47 | 22.01 | 19.45 |
| 監聽擷取相對於獨立數位擷取的時間差 | −1.94 | −1.94 | −1.69 |
| 監聽擷取到 ASIO 輸出回呼 | 45.13 | 48.59 | 30.14 |
| ASIO 輸出回呼到 MAIN USB 波形 | 14.95 | 14.50 | 14.59 |
| **電腦數位回錄到 MAIN USB** | **58.14** | **61.15** | **43.04** |
| 首個 Clock 到 MAIN USB | 77.61 | 83.15 | 62.49 |

原始的六次是前輪未加探針的錄音，本輪另以交錯順序測 40 與 20 ms。表中的負值來自兩個獨立的 Windows 回錄回呼觀察同一個端點。原來的 45.13 ms 內，帶有同一個銅鈸起音的輸入區塊抵達至輸出區塊回呼平均隔了 34.41 ms。其餘約 10.72 ms 反映以取樣點對齊區塊起訖的差異。這兩者都已包含在 45.13 ms 裡。

SoundCraft 的播放與混音位於數位擷取之前。前輪另加探針的六次精確起播，從 MIDI 輸入到音訊回呼收到播放命令平均 6.05 ms，再到首個混音區塊完成平均 4.62 ms。這些是不同批次的經過時間，包含等回呼與排程，不能從未加探針的 19.47 ms 精確拆出純 CPU 或驅動成本。數位擷取之後的 58.14 ms 走的是外部監聽與回錄路徑。[前輪軟體探針](chorus-dispatch-final/final-acceptance.json)

本輪只調整測試用監聽預填，ASIO 保持每區塊 256 個取樣。預填從 40 降到 20 ms，數位到 MAIN 的平均縮短 18.11 ms。另把同一個銅鈸的已錄波形直接寫入 ASIO，略過 SoundCraft 與監聽佇列；六次到 MAIN 的平均為 14.67 ms（14.38–15.61 ms）。均以驅動回報的輸入時間校正。末段包含驅動、Model 12 和 USB 回錄，這次接法無法分開驅動單向輸出、硬體內部與回錄各自的耗時，也沒有量到喇叭的聲學延遲。

每種預填各測四次 8.000 秒、兩次 8.125 秒。數位、監聽輸入、ASIO 輸出、MAIN 四處皆為 **8/8 次精確起播各一聲、4/4 次晚起播均零聲**。十二次都收到 SPP、Continue、144 個 Clock、Stop；獨立比對後續伴奏，在數位與 MAIN 均高於 0.99。由起播前 20 ms 至 Stop 後 120 ms，監聽端均未記錄供樣不足、佇列溢出裁切或 ASIO 異常旗標。這輪改善來自外部監聽預填。原 PR 增補圖與量測證據，既有起點音符與首 Clock 派送回歸均已重跑通過。

![首 Clock 到各個錄音點及兩種監聽預填的實測](chorus-main-return-split/midi-clock-main-return.png)

[前輪六次原始數據](chorus-dispatch-release/final-acceptance.json) · [十二次逐段數據及訊號完整性](chorus-main-return-split/per-take.json) · [獨立 ASIO 校驗](chorus-main-return-split/asio-control.json) · [分段統計](chorus-main-return-split/stage-summary.json) · [重新計算](chorus-main-return-split/summarize.py) · [回歸結果](chorus-main-return-split/transport-regression.log) · [PR #1669](https://github.com/storytold/soundcraft/pull/1669)

### SoundCraft 直接從 Model 12 ASIO 9/10 播放

使用同一份 48 kHz 八小節 S-MU2000 伴奏的原檔副本，在記憶體將主立體聲路徑起始通道設為 8（實體 9/10）。使用 Model Mixer ASIO、44.1 kHz、每區塊 256 個取樣。實體 MIDI 迴路為 Model 12 USB MIDI → DIN OUT → UM-ONE；每次 120 BPM、SPP、Continue、144 個 Clock、Stop。執行檔為 #1669 的 `2b53c7e` 與含 #1634 的 #1635 `7e922669` 本機整合版，加上僅供量測的 MAIN 輸入樣本擷取。原專案 SHA-256 為 `992c9ea2e252052261f326a03be545683f3bf9a59d1db5ab166a0acc1d5a7071`。[路由與實際開啟的裝置](chorus-direct-asio/route.json) · [執行檔與伴奏識別](chorus-direct-asio/control.json)

| UM-ONE 首個 Clock 到 Model 12 MAIN USB 銅鈸起音 | 平均與範圍，四次 8.000 秒起播 |
|---|---:|
| 上一輪外部監聽轉送，20 ms 預填 | 62.49 ms (57.47–65.47) |
| SoundCraft 直接 ASIO 9/10 | **28.07 ms (24.21–32.03)** |

直接輸出的四次逐筆為 32.03, 27.57, 28.45, 24.21 ms，平均比前輪縮短 **34.42 ms**。精確起播四次在 MAIN 各收到一次銅鈸；從 8.125 秒起播的兩次均沒有補播。六次都有後續伴奏（與前輪參考波形比對最低 0.994），停止後還繼續擷取約 1.5 秒，整段一併計算起音數。

兩輪都以獨立 UM-ONE 接收第一個 Clock 的主機時間為零點，以 MAIN USB 11/12 相同銅鈸模板及 0.90 相關門檻判定起音，逐區塊校正驅動回報的 6.80 ms 輸入延遲。本輪驅動拒絕第二個程式同時開啟 ASIO 輸入，因此從 SoundCraft 自己的雙向串流擷取 MAIN，樣本交給背景執行緒存檔，整段區塊序號連續。輸出仍由產品原有 ASIO 路徑直接送到 9/10。比較值來自前後兩批錄音，包含 MIDI 接收觀測與音訊回呼取樣時機，未量喇叭的聲學延遲。

![直接 ASIO 與 20 毫秒監聽預填的逐次實測](chorus-direct-asio/midi-clock-direct-asio.png)

[本輪逐次結果](chorus-direct-asio/per-take.json) · [前輪數據](chorus-main-return-split/per-take.json) · [首音 WAV](chorus-direct-asio/exact-a.wav) · [晚起播 WAV](chorus-direct-asio/late-a.wav) · [實體接收與時間戳](chorus-direct-asio/exact-a.json) · [重算腳本](chorus-direct-asio/analyze.py) · [PR #1669](https://github.com/storytold/soundcraft/pull/1669)


### Model 12 直接 ASIO 9/10 的緩衝與音訊完整性

使用上一節的本機整合版本、同一份八小節 S-MU2000 伴奏及 Model 12 USB MIDI → DIN OUT → UM-ONE 實體迴路。Model Mixer Settings Panel 顯示軟體 V2.20 0042、韌體 V1.30 0088、44.1 kHz。原廠面板維持 256 時，SoundCraft 要求 128、64 皆實收 256。調整面板後重開串流，檢查輸入與輸出的每一個擷取區塊。結束時已恢復原有 256，並重新量到雙向 256。

| 實際輸入／輸出（取樣） | 第一個 Clock 至 MAIN 平均（範圍） | 波形偏差次數 | 音量驟降視窗 |
|---|---:|---:|---:|
| 256 / 256 | 27.20 ms (23.59–32.43) | 1/12 | 0 |
| 128 / 128 | 21.52 ms (18.97–26.59) | 2/12 | 1 |
| 64 / 64 | 15.33 ms (12.87–21.14) | 4/12 | 0 |

每檔分兩次開啟串流，每次四次精確起播、兩次晚起播。全部 24 次從 8.000 秒起播都只收到一次銅鈸，12 次從 8.125 秒起播均無補播；36 次 MAIN 回錄都有後續伴奏，與同一參考片段的最低相關係數為 0.991。每次實收 SPP、Continue、144 個 Clock 與 Stop，回錄涵蓋停止後至少一秒。延遲的零點是 UM-ONE 第一個 Clock 的主機時間，以相同銅鈸模板估計 MAIN 起音，逐檔扣除驅動回報的 6.803／3.900／2.449 ms 輸入延遲。表中延遲包含首次起播。64 比本輪 256 平均縮短 11.86 ms。上輪獨立的 256 對照為 28.07 ms。

音訊完整性以 SoundCraft 剛混好的 9/10 與同時回錄的 MAIN 11/12 做比較。每次固定一個整數取樣位移及一組立體聲增益，再比較全段。任一聲道相鄰樣本的殘差變化超過 16 個 16-bit PCM 單位列為一次有偏差的錄音。每 64 個取樣另查預期 RMS >30、實際 RMS <預期 20% 的視窗。兩項指標可重疊。低緩衝首輪與重開後第一遍都出現波形偏差；不能據此斷定是驅動漏交區塊或演奏時聽得到爆音。所有回錄的診斷區塊序號連續，沒有削波。額外在乾淨錄音副本注入 64 個取樣的靜音與單點 +256 的脈衝，兩者皆成功偵測。本輪使用背景寫檔的雙向診斷版，未量喇叭聲學延遲或長時間演出穩定性。

波形偏差出現於 256 的 repeat2-256/exact-a；128 的 panel-128/exact-a, repeat-128/exact-a；64 的 panel-64/exact-a, panel-64/exact-b, repeat-64/exact-a, repeat-64/late-b。完整逐次數據含相關值、錄音峰值、殘差與序號。第一次恢復 256 時，測試控制端在開啟裝置階段逾時，未送 MIDI；重新啟動後完成該檔第二批。

![各實際緩衝的逐次起播與波形偏差](chorus-direct-asio-buffers/midi-clock-asio-buffer-sizes.png)

[全部逐次數據](chorus-direct-asio-buffers/metrics.json) · [分析程式](chorus-direct-asio-buffers/measure.py) · [音訊完整性檢查](chorus-direct-asio-buffers/quality.py) · [偵測器對照](chorus-direct-asio-buffers/detector-controls.json) · [只改主機至 128](chorus-direct-asio-buffers/host-128/actual.json) · [只改主機至 64](chorus-direct-asio-buffers/host-64/actual.json) · [實收 128](chorus-direct-asio-buffers/panel-128/actual.json) · [實收 64](chorus-direct-asio-buffers/panel-64/actual.json) · [復原後實收 256](chorus-direct-asio-buffers/repeat2-256/actual.json) · [128 疑似瞬斷 MAIN](chorus-direct-asio-buffers/repeat-128/exact-a-in.wav) · [對應送出的音訊](chorus-direct-asio-buffers/repeat-128/exact-a-out.wav) · [64 晚起播 MAIN](chorus-direct-asio-buffers/repeat-64/late-b-in.wav) · [PR #1669](https://github.com/storytold/soundcraft/pull/1669)


### Model 12 低緩衝的波形定位與盲聽

同一份八小節 S-MU2000 專案，維持 44.1 kHz，Model 12 USB MIDI → DIN OUT → UM-ONE，SoundCraft 直出 ASIO 9/10，以 MAIN USB 11/12 回錄。先重算前輪的同步雙軌 WAV，再次開啟 SoundCraft，將診斷取樣點移到寫入 ASIO 回呼的樣本完成裝置格式轉換之後，並分開計時混音、VST3 啟動及實際的外掛處理呼叫。量到的是主機經過的時間，包含執行緒排程。

| 首個有聲區塊 | 區塊預算 | 回呼內處理 | 外掛 setProcessing | 外掛 process | 處理播放命令等（drain / follow） |
|---|---:|---:|---:|---:|---:|
| 原專案，128 取樣 | 2.90 ms | 10.64 ms | 0.334 ms | 10.04 ms | 0.017 ms |
| 原專案，64 取樣 | 1.45 ms | 7.28 ms | 0.362 ms | 6.78 ms | 0.009 ms |
| 只移除主歌貝斯 VST3 指派，64 取樣 | 1.45 ms | 0.12 ms | 0 | 0 | 0.009 ms |

- **128 取樣的原始低電平段。** 以整段錄音對齊，從算出的銅鈸起音後 4.35 ms 起，連續 64 個取樣的立體聲 RMS，輸出折算到 MAIN 電平為 98.4，MAIN 實錄為 14.9（16-bit PCM 單位）。該段附近有連續 93 個 MAIN 取樣的雙聲道絕對值都低於 4。獨立 ASIO 程式把同一份已算好的音訊原速原電平送進 9/10，沒有觸發掉音或脈衝檢查。新開 SoundCraft 時再次錄到首音波形偏差，兩次 128 實測都未重現完全相同的 64-sample 低電平視窗。
- **64 取樣的四次異常。** 兩次發生在新開串流的第一個銅鈸。另兩次可用前後兩個固定延遲解釋：晚起播錄音在第一個伴奏音後約 1.289 s 轉移 5 個取樣，另一段在約 2.943 s 轉移 6 個取樣。容許該次相對位移後，整段的最大相鄰殘差變化分別為 2.33 與 2.22 個 PCM 單位。直接經原廠 ASIO 重播三個代表性原始 64 取樣輸出，也都通過檢查。
- **外掛與主機的界線。** 原專案只有主歌貝斯使用 S-MU2000 VST3；銅鈸、Kick、Snare、Hat 是四支 Sampler。主要耗時落在首次進入貝斯外掛的處理函式內。早先把副本的 instrument.bypass 欄位設為 true 時，探針仍量到 VST3 呼叫，故未採用為移除外掛的對照。改為在另一份副本移除該單一指派後，首個有聲區塊內的 VST3 呼叫數為零，六次 MAIN 回錄都通過原先的波形檢查。波形異常可界定在混音輸出到 MAIN 回錄之間；現有取樣點不能再區分 ASIO 驅動、硬體處理與回錄各自的責任。
- **起播驗收。** 原檔三批，共 18 次。8.000 秒 12 次各有一個銅鈸；8.125 秒 6 次均無補播，後續伴奏全部匹配。每次實收 SPP、Continue、144 個 Clock 與 Stop。兩種修改副本各另做六次，均未計入原檔驗收。完成後原廠面板已恢復 256 取樣。PR 新增實錄圖與量測說明，未發現須修改 Clock follower 的證據。

![128 取樣的音量驟降與 64 取樣的時間偏移](chorus-direct-asio-buffers/waveform-followup/midi-clock-asio-waveform-detail.png)

**聽感待本人確認。** 盲聽檔每段 2.65 秒，A 與 B 之間停 0.85 秒，順序已保存。每對採用同一增益與淡入淡出，沒有壓縮或慢放。[128 首音 A/B](chorus-direct-asio-buffers/waveform-followup/listen-128-AB.wav) · [64 首音 A/B](chorus-direct-asio-buffers/waveform-followup/listen-64-cold-AB.wav) · [64 晚起播 A/B](chorus-direct-asio-buffers/waveform-followup/listen-64-AB.wav)

[逐次外掛計時](chorus-direct-asio-buffers/waveform-followup/foreign-calls.json) · [時間位移分析](chorus-direct-asio-buffers/waveform-followup/offset-change.json) · [128 原始取樣重播](chorus-direct-asio-buffers/waveform-followup/replay-128.json) · [64 原始取樣重播](chorus-direct-asio-buffers/waveform-followup/replay-64.json) · [實體 MIDI 逐次複驗](chorus-direct-asio-buffers/waveform-followup/retest.json) · [本機診斷取樣修改](chorus-direct-asio-buffers/waveform-followup/timing-probes.patch) · [PR #1669](https://github.com/storytold/soundcraft/pull/1669)


### S-MU2000 播放前預熱

原版首次音訊處理在 128／64 取樣分別量到 10.04／6.78 ms。預熱專案狀態後，兩次獨立冷啟動分別為 1.662–1.669／1.109–1.322 ms。Model 12 MAIN 共回錄 24 次，8.000 秒各響一次銅鈸（16/16），8.125 秒均無補播（8/8）。64 取樣其中一次整個回呼只餘 0.003 ms。驗收後面板恢復 256 取樣，聽感待盲聽。[本機驗收、修正與量測圖](chorus-direct-asio-buffers/smu-prewarm/REPORT.zh-TW.md)

### 預熱後的 64／128 取樣十分鐘長播

64 取樣的五次冷啟動均有至少 0.161 ms 餘裕，但持續播放時 413,434 個回呼中有 8 個各別超時，最慢 2.943 ms。MAIN 回錄另確認一次至少 1.45 ms 的音量驟降，與最近的回呼超時相距 22.05 秒。128 取樣的 206,718 個回呼均在預算內，最慢仍餘 0.512 ms，回錄沒有達到相同門檻的掉音。兩組各自從 8.000 秒起播 5 次，銅鈸每次只響一次；從 8.125 秒起播各 5 次，均未補播。面板已恢復 256 取樣，聽感待本人盲聽。[十分鐘實測、計時圖與 MAIN 波形](chorus-direct-asio-buffers/smu-prewarm/soak/REPORT.zh-TW.md)

### 第 486.242 秒掉音追查

逐樣本比對確認，64 取樣第 486.242 秒的 MAIN 回錄插入 **107 個近靜音取樣（2.426 ms）**；先前的 1.45 ms 是偵測視窗長度。原始兩次區塊處理開始相隔 6.518 ms，其中 6.099 ms 落在兩段工作之間。以獨立 ASIO 客戶端重送同一段 PCM，正常交付時兩組均為 0/4，刻意延後交付時 64／128 取樣分別有 3/4、2/4 出現同型缺口。原專案另做 12 次實體 MIDI 起播，8.000 秒共 8 次各響一次，8.125 秒共 4 次均無補播。盲聽待本人回家。[實機重播與逐樣本驗收](chorus-direct-asio-buffers/smu-prewarm/soak/dip486/REPORT.zh-TW.md)

補做 64 與 128 取樣各 9 分鐘的同步排程、DPC、USB 與音訊擷取。最長回呼外空檔分別為 2.1298、3.5393 ms。兩輪都未重現第 486.242 秒的 107 取樣插入。逐次核對 64 取樣的 8 次超時，在第 13.498 秒附近的 MAIN 找到另一處 40 取樣（0.907 ms）的近靜音插入，接點在 #37504 開頭。同段 ASIO 輸出與 128 取樣對照連續。逐包比對發現該處 USB OUT 提交相隔 2.0199 ms，USB IN 最大間隔 1.0445 ms，雙向均無缺幀或封包錯誤。現有資料無法定位是哪一段產生近靜音。64 取樣最長一次有 2.0841 ms 在等待，0.0044 ms 在等 CPU，期間 Model 12 播放端點完成兩筆傳輸。詳見[回呼空檔實機驗收](chorus-direct-asio-buffers/smu-prewarm/soak/etw-gap/REPORT.zh-TW.md)。

