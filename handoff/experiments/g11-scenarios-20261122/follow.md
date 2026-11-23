# 外部 MIDI Beat Clock 跟隨的情境驗證

本輪使用 #1669 的 `6b82d9bc84af17b259b98970dc5557a93c80d7a0` 和本機測試。A-1、A-2、A-3 以獨立計算的主機脈衝作參考，經正式 MIDI 輸入、跟隨器及實際供未來音訊使用的 tempo map 更新函式，設定 30 ms 的已提交音訊範圍。將八分音符交給內建 sampler 和離線 mixer，每個音送 96 個取樣的已知 PCM 脈衝，掃描輸出波形第一次越過 0.001 的取樣。誤差定義為輸出起音減去外部參考。這些是可重跑的軟體數據，未包括實體 USB、驅動和控制台往返延遲。B-6、D-1、D-6 與 C-8 的校準設定由整合報告另列。

| 情境 | 結果與量測 | 可重跑的測試名 |
|---|---|---|
| A-1　推速 | 未達提議目標。124→124.3→124 BPM，各 16 小節，257 個起音，在理想、±1/±2 ms 到達抖動下最大誤差依序為 3.104、3.062、3.792 ms。32 小節 +8% 再回到 124 的 513 個起音最大誤差 7.729、7.875、7.938 ms；−8% 再回升為 8.979、8.854、9.062 ms。九組皆無誤觸 step recovery。含取得期的相鄰 BPM 讀值最大變化 7.226，第一拍過後的最大變化為 0.091，符合穩定區 0.1 的目標。即使無抖動，兩個大幅漸變也未達 4 ms 目標。 | `scenario_a1_pitch_fader_rendered_hats` |
| A-2　突然變速、C-8 四種取樣率 | 通過。128→140 與 140→128 在第 384 個脈衝（小節線）和第 396 個脈衝（拍中）改速。44.1、48、96、192 kHz 共 16 組；轉速後第一個八分音符 −4.312 至 +3.492 ms，再往後至第 8 拍結束最大絕對誤差 0.750 ms。逐音帶符號數據見原始紀錄。 | `scenario_a2_drop_rendered_eighth_notes` |
| A-3　換播放機 | Stop 在約 8.137 s 發出停止，後續純 F8 維持停止。Coast 模式 120→128 BPM，舊來源第 8 秒開始斷流，新來源首個 F8 在 8.300 s，到測試結束仍為 Coasting。觀察到 65 個對應的起音，末音晚 473.438 ms。跟隨器在失鎖時清掉 awaiting_clock，之後只在該旗標重新設起時轉回 Locked；純 F8 不會設起。需決定允許直接跟隨新相位，或要求 DJ 送 Start/Continue。 | `scenario_a3_resume_pulses_without_start` |
| A-4　軟體埠群聚 | 三輪各 10 分鐘、28,800 pulses；3/4/5 個一組，組內相隔 0.2 ms。三者全程保持 Locked，0 次失鎖。前 192 pulses 為 BPM 取得期，之後 0 次假 step，BPM 範圍分別為 119.9871–120.0258、119.9710–120.0484、119.9810–120.0192。 | `scenario_a4_ten_minutes_of_bunched_clock` |
| A-5　待機時持續送鐘 | 50 個 Start 都在 0，50 個 Continue 都在最後的 SPP，總計 100 個 Stop。另走實際音訊 callback 和測試樂器，100 個按音中 58 個收到顯式 note-off，其餘 42 個在聲音仍在時由 plugin reset 清除。每次停止都沒有持續的音。本計畫另指定一個 note-on 對一個 note-off，這個字面條件未達，紅測保留；尚無外部樂器卡音的證據。本機 upstream/main b5392da 的 playback callback 在 Cmd::Stop 已呼叫 mix.reset()，#1669 的 halt() 沿用。若要求所有樂器在 Stop 都接收逐音通知，這是共用播放層的政策問題。 | `scenario_a5_random_phase_transport`、`scenario_a5_notes_released_across_random_stops` |
| A-6　六小時 | 已執行 ignored 測試。模擬輸入 1,168,942 個脈衝、63 次變速。排除變速後前 5 秒，各小時的最大網格誤差 4.042、4.562、4.542、4.458、4.688、3.354 ms。六次讀取的累計 tempo 事件數為 529、959、1387、1759、2239、2703；末次保留事件的有效資料為 43,248 bytes（不含容器預留容量、其餘 session 與程序）。單次取出的 transport 指令最多 2 筆，reader 固定容納 32 筆。長時間持續增加的歷史節奏事件數未顯示固定上界。每小時結束前最後一個穩定四分音符另經 sampler 與 mixer 渲染，六個實際起音誤差依序為 +2.562、−0.979、+1.271、−1.667、+0.271、−1.312 ms。 | `scenario_a6_six_hours_of_seeded_steps` |
| D-2　循環加外部定位 | 本機 Loop Playback 設為開，選區 [24,000, 60,000) samples。SPP 6 / 20 + Continue 分別從 36,000（區內）、120,000（區外）起播，兩次本機 loop 選項都保留，活動範圍都是 None。產品要保留此外部主控優先規則或另設行為，列為 Open question。 | `scenario_d2_local_loop_is_ignored_under_external_positioning` |
| E-1　交錯 realtime/MTC | F8、FA、FC 混入 MTC full frame 與 quarter-frame 訊息，Clock 端兩次均得到 Locate(0)、Play(0)、Stop。MTC 端的完整時間碼解碼見同行的 MTC 測試。 | `scenario_e1_clock_interleaved_in_timecode` |
| E-3　SPP | 不合法的高位資料中斷 SPP，無定位。連續 SPP 16383、3 產生 98,298、18 個 MIDI Clock 脈衝的定位；Continue 從 18 起，播放中的 SPP 被略過。播放中收到 SPP 的產品政策列 Open question。 | `scenario_e3_song_pointer_during_play_and_at_rest` |
| E-4　極端速率 | 每 10 秒 1 pulse、共 60 個：最終 Coasting。每秒 10,000 pulses、共 100,000 個：最終 Locked。兩者皆不提供有效 BPM，佇列最高 2，無 panic。狀態為 reader 提供給畫面的欄位。 | `scenario_e4_extreme_clock_rates` |
| E-5　隨機輸入 | 每次注入 1 byte，共 10,000,000 bytes，固定種子 20261122；每 50 bytes 取走累積的事件。沒有 panic，固定大小的 reader 為 4,608 bytes，事件佇列最高 6/32。 | `scenario_e5_clock_ten_million_stream_bytes` |

## 原始紀錄與重跑方法

[Clock reader、隨機走帶、音符釋放](follow-reader.log) · [A 組離線波形與 D-2](follow-ui-final.log) · [六小時](follow-long-final.log)。每輪測試均無需實體操作。

使用該 checkout 的本機工具鏈及相同 target 目錄。前兩個指令遇到文件的未達條件會回傳失敗碼，測試保留供後續處置。

```powershell
& E:/soundcraft/tmp/1669-coderabbit-final/stack-build.cmd test --lib -p soundcraft-playback performance_scenarios -- --nocapture
& E:/soundcraft/tmp/1669-coderabbit-final/stack-build.cmd test --lib -p soundcraft-ui-egui performance_scenarios -- --nocapture --test-threads=1
& E:/soundcraft/tmp/1669-coderabbit-final/stack-build.cmd test --lib -p soundcraft-ui-egui scenario_a6_six_hours_of_seeded_steps -- --ignored --nocapture
```

音訊探針採離線 render。此處的 jitter 來自可重現的輸入時間序列，沒有宣稱實體控制台或其他廠牌的端對端精度。已檢查 playback、mix、ui-egui，未找到涵蓋本測試的音訊執行緒配置追蹤器；這次的記憶體量測沒有驗證回呼零配置。

## 電子舞曲 80 → 130 → 80 BPM

`scenario_edm_eighty_one_thirty_eighty_rendered` 從頭到尾只送一次 Start，以同一條外部 Clock 持續演奏 24 小節。每段 8 小節、4/4、48 kHz，使用可辨識波形的打擊樂測試音色。每個部分先離線產生一條連續音軌，再以等增益相加檢查混音。數字為辨識到的 PCM 起音與獨立主時鐘的差，正值代表較晚。

| 段落 | 踩鈸數／底鼓數／小鼓數 | 踩鈸最大絕對誤差 | 底鼓最大絕對誤差 | 小鼓最大絕對誤差 | 各部最後一音誤差（踩鈸／底鼓／小鼓） |
|---|---:|---:|---:|---:|---:|
| 開頭 80 BPM | 64／16／16 | 0.000 ms | 0.000 ms | 0.000 ms | 0.000／0.000／0.000 ms |
| 改 130 BPM | 64／16／16 | 17.896 ms | 1.625 ms | 3.562 ms | −1.729／−1.625／−1.688 ms |
| 回 80 BPM | 64／16／16 | 70.104 ms | 5.875 ms | 15.125 ms | +4.750／+5.875／+5.521 ms |

總計踩鈸 192、底鼓 48、小鼓 48，混音波形中共有 192 個不同時間的起音。每部最後一音皆完整保持 96 samples，曲終另檢查 1 秒靜音無額外起音。末段三個聲部的最後一擊都超過提議的 4 ms，保留 #1669 的紅測以供評估。這是極端外部變速下的渲染偏差；用例沒有發現少播、重播或尾音被剪掉。[逐段 PCM 資料與測試結果](follow-edm-24bars.log)

```powershell
& E:/soundcraft/tmp/1669-coderabbit-final/stack-build.cmd test --lib -p soundcraft-ui-egui scenario_edm_eighty_one_thirty_eighty_rendered -- --nocapture
```
