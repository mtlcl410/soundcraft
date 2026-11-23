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
