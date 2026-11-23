# Model 12 錄 SD 並送 MTC：跨次起音調查

2026-11-21。專案、設備和格式與[三輪原始驗收](../ROUND4-ACCEPTANCE.zh-TW.md)相同。比較的標記為歌曲第 5.000 秒的 A4。

## 既有錄音

| 歌曲比較 | 波形對齊的差距 ms | 減去最近整格後 ms | 減去最近 quarter-frame 後 ms |
|---|---:|---:|---:|
| 0004 → 0007 | +38.188 | +4.855 | −3.479 |
| 0004 → 0009 | +41.750 | +8.417 | +0.083 |
| 0007 → 0009 | +3.562 | +3.562 | +3.562 |

30 fps 每格 33.333 ms，quarter-frame 間隔 8.333 ms。最大的差距接近五個 quarter-frame，另外兩對的殘差各約 3.5 ms，三次結果不足以證明量化。另以同一鋼琴起音搜尋五首歌的 SD MAIN 右軌，歌曲 0004、0005、0006、0007、0009 依序為 +13.500、+49.146、+49.667、+51.688、+55.250 ms，相關係數均高於 0.98。0005、0006 缺少獨立音軌，只作旁證。[相位統計](three-run-phase.json) · [MAIN 起音交叉核對](main-anchors.json)

三輪獨立 DIN 側錄在回呼入口使用主機單調時間戳。連續訊息間距的中位數 8.335–8.338 ms。用 A4 前後一秒的完整群組推算 MIDI 的歌曲時間原點，各輪群組起點的第 5 至 95 百分位散布都小於 0.15 ms。SoundCraft 回報同段的輸入抖動 p95 中位數為 0.667 ms，驅動時間映射後的到達延遲 p95 中位數為 0.717–0.952 ms。這些數據衡量相鄰訊息與回呼交付的變化；固定的發碼或音訊路徑延遲仍需獨立對照。

再以每個音各自的 75 ms 波形比較不同歌曲。相對 0004，0007／0009 在第 4 秒分別晚 38.188／41.250 ms，第 5.5 秒晚 30.208／33.750 ms，第 17 秒晚 30.208／33.771 ms。這說明差異延續到起播後，且並非整首歌都固定差 42 ms。[逐音對齊](note-alignment.json)

## 鎖定計算與 Windows 時間戳

在 #1663 的 ee80920，WinMM 的驅動毫秒時間戳轉成微秒，DriverTime 以短時間窗的最小交付延遲將其映射到主機單調時鐘。Reader 要看到兩個連續、標籤相差兩格的完整群組才鎖定。在第 7 號訊息時間，Reader 取群組標籤加七個 quarter-frame，並擬合最近群組的時間。音訊回呼再加上該時間戳到當下的經過時間及裝置回報的呈現延遲。第一組第 0 號到第 7 號間有七個間距；下一組第 0 號才滿八個。三輪實測前者 58.213–58.328 ms，第一組第 0 號到第二組第 7 號為 124.958–125.009 ms。這段啟動確認時間與第 5 秒 A4 的偏差是兩個量。若先前已有停止定位，首個音訊區塊可從該定位開始以保留首音；後續的定位修正另外有一格誤差門檻和持續時間條件。詳細的時序測試重跑六項通過。[Reader](https://github.com/storytold/soundcraft/blob/ee8092029b37dac7699b6f15bd26a993f6370a54/crates/playback/src/mtc_input.rs) · [音訊回呼](https://github.com/storytold/soundcraft/blob/ee8092029b37dac7699b6f15bd26a993f6370a54/crates/playback/src/callback.rs) · [驅動時間映射](https://github.com/storytold/soundcraft/blob/ee8092029b37dac7699b6f15bd26a993f6370a54/crates/playback/src/sync_input.rs) · [六項測試](compiled-reader-regressions.log) · [MTC 格標籤與兩格補償的協定背景](https://www.rfc-editor.org/rfc/rfc6295.html#appendix-B.4)

## 追加實錄方法

每次建立 48 kHz／24-bit 新歌，保持同一份伴奏、音訊端點、Frames 8 和低監聽音量。各輪保留 SD 的 CH1 現場麥克風與 CH2 電腦回送。以 DIN 封包的驅動時間戳和 QPC 回呼時間記錄第一組與鎖定。Windows 同時以 WASAPI 擷取 Model 12 播放端數位回送、Model 12 的 USB 音訊輸入；兩路紀錄每個封包第一個音訊 frame 的 QPC 時間和不連續旗標。CH1 的兩次短音用來把 SD 樣本位置對到 USB 輸入時間，CH2 的 A4 用同一個 75 ms 樣板定位。對齊時剔除含不連續或不可信時間戳的窗口，並檢查兩個麥克風標記的估計是否一致。這套設備可比較哪一段的延遲跨次變動；要分開 Model 12 的絕對發碼偏移與 USB 輸入的固定延遲，仍需獨立校準。[WASAPI 封包時間戳定義](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer)

初次方法校準由操作者指定重錄，從統計排除。0011～0020 每首各有一份 CH1 與 CH2 的 SD WAV，原檔均以 SHA-256 核對。0016 的電腦錄製器在端點失效後重新開啟，未涵蓋這首；其餘九首都以同一把主機 QPC 時鐘量到 Windows 播放端與 Model 12 USB 錄音端，並以 CH1 兩個獨立聲音配對。0016 的 2 秒起點依操作者回報。

| SD 歌曲 | 起點 s | SD 的 A4 晚 ms | Windows 播放端相對 DIN 晚 ms | CH1 的 USB 錄音時間原點相對 DIN ms |
|---|---:|---:|---:|---:|
| 040208_0011 | 0 | 13.896 | 11.583 | 29.944 |
| 040208_0012 | 0 | 51.375 | 49.689 | 29.948 |
| 040208_0013 | 0 | 47.979 | 46.454 | 30.173 |
| 040208_0014 | 0 | 56.417 | 54.799 | 30.212 |
| 040208_0015 | 0 | 55.146 | 53.643 | 29.900 |
| 040208_0016 | 2（面板） | 51.250 | — | — |
| 040208_0017 | 2 | 49.146 | 47.614 | 30.034 |
| 040208_0018 | 2 | 56.771 | 55.173 | 29.930 |
| 040208_0019 | 2 | 55.125 | 52.751 | 29.859 |
| 040208_0020 | 2 | 53.271 | 51.349 | 29.888 |

十首 SD 起音的範圍為 +13.896～+56.771 ms，中位數 +52.323 ms，極差 42.875 ms。九首完整分段擷取中，Windows 播放端相對 DIN 的極差已達 43.590 ms。SD 和播放端兩欄逐輪相減的差值只在約 1.5～2.4 ms 間變動。用兩個麥克風標記獨立對齊，USB 輸入時間原點相對 DIN 的九輪極差為 0.353 ms；將 SD 上的鋼琴位置換算成這個 USB 輸入時鐘後，和 Windows 播放端的差值為 31.403～32.256 ms。這是包含回送與擷取時基的合計值。這組試驗將約 43 ms 的跨次變動定位到 Windows 播放端或更早；Model 12 的 SD 錄製、返送、擷取的跨次變化無法解釋該極差。沒有獨立的電氣與取樣時鐘校準，不能從 29.944 ms 的中位數推論 Model 12 本身的絕對發碼延遲。[十輪分布](distribution.json) · [單次四路對照](repeat01/partition.json) · [四首歌頭](series/partition.json) · [五首非零位置](series2/partition.json)

資料顯示 0011 在 Windows 播放端晚 11.583 ms，進出一次 STORAGE 後，0012～0015 均晚 46.454～54.799 ms。後續 2 秒起錄的完整四首晚 47.614～55.173 ms。第三批後半段診斷中，reported_lead_us 為零，lead_clamps 隨回呼增加，表示播放引擎拒用了裝置回報的呈現延遲。下方以相同輸入單獨驗證重開音訊的效果。[逐次呈現延遲診斷](series2-lead.jsonl)


![十首 SD 與 Windows 播放端的 A4 起音比較](ten-takes.png)

## 只重開 SoundCraft 音訊的對照

保持 Model 12 停止，循原有一般 USB MIDI → Model 12 DIN OUT → UM‑ONE 的實體路徑，逐次重送 0004 錄得的同一段 781 筆 quarter-frame，使用同一份 S‑MU2000 專案和鋼琴波形樣板。每次都以 UM‑ONE 實際收到的時碼計算，避免將電腦排程送出的瞬間當成到達。只重新套用該測試程序原本的輸出設定，裝置仍為 Model 12、48 kHz，整段未進 STORAGE 或改變硬體接線。兩個其他 SoundCraft 程序均已確認 MTC Offline，走帶停止。

| 音訊串流狀態 | Windows 數位播放端的 A4 相對 DIN 晚 ms | 中位數 | 引擎有效呈現延遲 |
|---|---|---:|---|
| 進出 STORAGE 後，原串流 | 50.861、50.298、48.713 | 50.298 ms | 全為 0；每次觀測窗拒用時間戳 283～292 次 |
| 同一程序重新開啟相同輸出 | 11.937、11.619、11.943、10.704、11.083 | 11.619 ms | 35.708～42.708 ms；各窗均無新增拒用 |

重開後第一輪的 WASAPI 數位回錄在起音搜尋範圍內標記 data discontinuity，已排除；表中保留其餘五筆有效結果。兩組中位數相差 **38.679 ms**。此對照量的是 Windows 播放端，並未再錄一首 SD 歌曲。[原狀及重開對照](autoA/result.json) · [重開後追加三次](autoB/result.json) · [回錄封包旗標](autoA/loop.csv)

**判定。** 在這台 Windows／Model 12 系統上，進出 STORAGE 曾使 WASAPI 音訊串流失效。SoundCraft 對遺失或超過一秒的呈現延遲採用零，直到重開裝置才恢復有效讀值。實機分段和同輸入對照都把主要跨次差距指向這條音訊呈現路徑。根據現有證據，無須調整 quarter-frame 解碼或加入固定毫秒補償；無法細分是哪一層最先提供了無效時間戳，也不能把剩下約 11.6 ms 全歸給 MTC。十輪原始 SD 驗收仍保留其跨次差距。MTC 協定精度上限及外接取樣時鐘的效果均未由這個測試證實。

**複測步驟。** 從 STORAGE 回歌曲畫面後，待 Model 12 音訊端點恢復，在 SoundCraft 停止時開啟 Setup → Playback Engine，以 Reconnect audio device 重開原輸出（本次自動對照透過重新套用相同的輸出設定達成）。確認裝置仍為 Model 12／48 kHz、輸出時間戳恢復有效，再開始新一輪。跨次比較應記錄是否重開，並保存 reported_lead_us 與 lead_clamps 的增量。[程式的重連與串流失效處理](https://github.com/storytold/soundcraft/blob/ee8092029b37dac7699b6f15bd26a993f6370a54/crates/ui-egui/src/app/audio.rs)

## STORAGE 後的輸出時間戳

**修正前基準。** 重開相同輸出後，五次數位回錄的 A4 落在 +10.70～+11.94 ms，極差 1.24 ms，符合本輪對跨次一致性的要求。未重開的三次相對此基準額外晚約 39 ms。當時播放引擎將無效的呈現時間戳換算成零延遲。第 0016 首仍保留 SD 成績，分段擷取缺失。

**歸屬。** 上游 main 的 85623f2 忽略輸出回呼的 OutputCallbackInfo。#1662 的 66542df 在共用 DeviceTiming 建構時把缺失或超過一秒的延遲轉為零，#1663 的 MTC 追隨與產生沿用這個時基。這次修正的歸屬是 #1662，共用層向下游傳遞延遲狀態，MTC quarter-frame 的解碼與鎖定計算維持原規則。[main 的音訊回呼](https://github.com/storytold/soundcraft/blob/85623f28f99a9a788123f0f6b48829f95f07962f/crates/playback/src/stream.rs) · [引入共用時間戳的提交](https://github.com/storytold/soundcraft/pull/1662/commits/66542df55c09f886b69bbef63a7dde25aaaa511e)

**舊版畫面。** 在此次 STORAGE 測試使用的同一個 ee80920 桌面程序，ui.inspect 與實際截圖都顯示底部狀態列寫有「Audio output」、Model 12 裝置名稱及「Reconnect audio device in Setup › Playback Engine」。程式記錄另有 StreamInvalidated。這直接證實此 STORAGE 情境出現過提示；原先十首並未逐首擷取畫面，無法追認每次出現的時刻。[狀態列截圖](storage-retest/original-storage-warning.png) · [狀態列原文](storage-retest/original-visible-status.json)

**新版驗收方法。** 使用同一份 S‑MU2000 專案、原有 48 kHz Model 12 播放端與同一段 781 筆 quarter-frame 的實體 MIDI 迴路。先取得正常基準，然後完整進出 STORAGE 三次，每次回到歌曲模式後只重開獨立錄音工具，SoundCraft 保持同一程序與輸出，不按 Reconnect、不重套音訊設定。每次記錄 A4 相對 DIN 的起音、波形相關、有效延遲及其來源，以及裝置警告。為使「數毫秒」可重算，本輪採用舊版重開後中位數 11.619 ms 前後各 3 ms 作為比較帶，另列實際差值。起音搜尋窗如有 WASAPI 不連續或無有效波形配對，保留原始紀錄並另取有效量測。如果輸出端只能警告，三次需逐一留存畫面，單獨報告時間是否達標。

### 第一次修正的實機結果（4ff8ced）

共用層將輸出延遲分為驅動實測、沿用同一串流上次有效回報、未知，另區別尚未收到回呼。舊版回歸測試重現了 15 ms 消失與新輸出把未知寫為零；修正後兩項通過。#1663 遇到未知延遲時不累積輸出相位誤差，驅動明確回報零時仍可校正。桌面程式由乾淨的 4ff8ced 建置，沒有私有補丁。

第一個程序的健康基準 +12.273 ms。進入 STORAGE 後狀態列出現失效提示；額外擷取螢幕時圖形引擎回報 Out of Memory，該程序結束，這次沒有起音結果。之後關閉先前留下的閒置測試程序，第二個程序的健康基準為 +3.680、+3.944 ms。計時檢查保留這個工作環境差異。

第二個程序完整進出一次 STORAGE，全程沒有重開音訊設定。失效前 15～1 秒的 69 筆健康回報為 42.437～43.958 ms（中位數 43.583 ms）；約在失效前 0.22 秒跳至 56.395 ms。這個值在合法範圍內，之後被持續沿用。第一次回錄的起音搜尋窗有不連續旗標，另錄一次得到 **−5.699 ms**（波形相關 0.99981，781 筆 quarter-frame），比同程序的健康基準中位數 3.812 ms 提早 9.511 ms。已重現只保留最後有效值仍會在重置邊界產生偏差；這一次不算最終三輪通過。[建置來源](../../1663-storage-candidate/build-origin.json) · [兩次正常基準](storage-retest/baseline3/result.json) · [進入 STORAGE 時的警告](storage-retest/cycle1-mounted.json) · [補錄成績](storage-retest/post1b/result.json)

### 自動恢復原輸出端點的三輪驗收

2026-11-22。在同一個正式 #1663 程序 `62ea084`（PID 19832）上連做三次完整 STORAGE 進出，操作員未按 Reconnect、未重套設定。沿用 48 kHz Windows 共用 WASAPI 輸出、S‑MU2000 專案與第 5.000 秒的 A4。每段皆由 Model 12 USB → DIN OUT → UM‑ONE 實際收到同一序列 781 筆 quarter-frame 驅動；回錄點在 Windows 數位播放端。這次沒有重新錄製 SD 歌曲。[乾淨建置來源與 SHA-256](../../1663-storage-auto-candidate/build-origin.json) · [程序與專案識別](storage-retest/final/process.json)

| 操作 | A4 相對 DIN | 與本程序進 STORAGE 前之差 | A4 附近有效呈現延遲中位數 | 波形相關係數 |
|---|---:|---:|---:|---:|
| [本程序基準](storage-retest/final/baseline/result.json) | +3.810 ms | — | 43.062 ms | 0.99998 |
| [第 1 輪返回](storage-retest/final/post1/result.json) | +3.321 ms | −0.489 ms | 46.176 ms | 0.99941 |
| [第 2 輪返回](storage-retest/final/post2/result.json) | +3.183 ms | −0.627 ms | 50.187 ms | 0.99937 |
| [第 3 輪返回](storage-retest/final/post3/result.json) | +3.181 ms | −0.629 ms | 46.125 ms | 0.99938 |

**恢復與跨次一致性通過。** 三次皆記錄到同一端點的新串流經驗證後接手。三個 A4 搜尋窗均取得有效匹配；A4 前 2 秒到後 1 秒的延遲來源皆為 `reported`，沒有新增拒用時間戳。三輪極差 0.140 ms，對當次 3.810 ms 基準最多相差 0.629 ms。共用層保留播放圖、外掛、MIDI reader 和設定，驗證候選串流的八個連續有效回報後才在停止時交接；獨佔 ASIO 維持原有開流方法。[串流恢復日誌](storage-retest/final/desktop.log) · [三輪逐筆狀態](storage-retest/final/storage-cycles.jsonl)

**歷史絕對值比較未達標。** 三輪均早於舊基準 11.619 ms 約 8.3～8.4 ms，超出事先訂定的 ±3 ms 比較帶。關閉先前的測試程序後，第一次候選版的正常基準也改變。正式三輪結束後，另開原版 `ee80920` 在當下環境、相同專案和硬體路徑比對兩次，正常新串流的 A4 分別為 +2.786、+3.759 ms。這證明原版在當下也可得到約 3 ms 的結果；資料無法把跨環境的絕對差值歸因給特定元件。保留歷史數據與當次基準，兩組各自報告，不加入固定補償。[原版對照一](storage-retest/old-control/control1/result.json) · [原版對照二](storage-retest/old-control/control2/result.json)

**警告。** 舊版的實際截圖已核對。正式版在 STORAGE 顯示裝置無法使用的狀態；自動恢復後，醒目提示可消失，底部狀態在此次實測版仍保留過時的重連指示。純 UI 修正 91366d0 在成功交接後清除仍屬於這次故障的閒置提示；其他較新的訊息及錄音中斷時保留 take 的提示仍可讀。修正前同一 UI 回歸失敗，修後通過。合入 #1663 的 0819e61 與實機版 62ea084 的 crates/playback Git tree 完全相同，兩者只差兩個 UI 檔案。狀態列清除另以軟體驗證，三次實錄仍歸屬於 62ea084。[第 1 輪進入狀態](storage-retest/final/cycle1-mounted.json) · [第 1 輪恢復後狀態](storage-retest/final/post1/after.json)

### Open questions for the user

未來是否要讓使用者選擇「停止時自動重建播放引擎」？目前手動重連會重建外掛實例與編輯視窗；是否接受這個操作代價屬於 SoundCraft 產品決策。Pro Tools 參考手冊的 MTC Reader／Generator 設定與 MIDI quarter-frame 的時間碼規則沒有為 Windows 音訊裝置重置指定此政策。本輪不將固定的 11.6 ms 寫入通用預設，外部校準應沿用該使用者的實際路徑。[Pro Tools Reference Guide](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2024.3.pdf) · [RFC 6295 附錄 B.4](https://www.rfc-editor.org/rfc/rfc6295.html#appendix-B.4)
