# 樂團排練驗收 · 同一段副歌從 120 降到 100 BPM

測試版為 SoundCraft #1669 的 67b3e50。使用上一輪的八小節 S‑MU2000 伴奏，原專案 120 BPM、4/4，兩次均從歌頭開始。按 TASCAM 的面板操作方式，在停止時變更速度，再重奏同一段；這可驗證兩種速度的跟隨與實際鼓點。連續播放中的瞬時變速需另有對應的輸入證據。

Model 12 產生 Clock/SPP，DIN OUT → UM‑ONE → SoundCraft，同時側錄 Model 12 USB MIDI。SoundCraft 伴奏送至 CH9/10，PC1X 從 CH2 LIVE 進 MAIN。電腦以 48 kHz 分別擷取數位伴奏、MAIN 混音與 CH2。每次播放比對整段 Clock 的平均 BPM、穩定段 SoundCraft 估計 BPM，以及錄音內相鄰小鼓起音的間距（兩拍）。120 BPM 每拍 500 ms，100 BPM 每拍 600 ms。另核對兩遍是否正常跟停。

[TASCAM Model 12 使用手冊，第 52 頁](https://www.tascam.eu/en/docs/Model12_OM_EFS_RevF.pdf#page=52)

## 本次結果

第一遍已完成。Model 12 的 DIN 速度為 120.014 BPM（754 個 Clock），SoundCraft 穩定段中位數為 120.006 BPM。數位伴奏與 MAIN 的小鼓均換算為每拍 500.34 ms，副歌銅鈸各一次，並正常跟停。[120 BPM 量測](tempo-a-result.json) · [MAIN 錄音](tempo-a-main.wav)。

| 本體設定 | DIN 實測 BPM | SoundCraft 穩定段 BPM | MAIN 每拍（由小鼓換算） | 第一個 Clock 到數位銅鈸 | 副歌小鼓實錄／譜面 |
|---|---:|---:|---:|---:|---:|
| 120 BPM | 120.014 | 120.006 | 500.34 ms | 7.995 秒 | 8／8 |
| 100 BPM | 100.008 | 100.004 | 600.19 ms | 9.597 秒 | 5／8 |

100 BPM 這遍從歌頭開始，UM-ONE 收到 1,208 個 Clock。Model 12 約 30.19 秒後才送 Stop，兩遍 SoundCraft 均跟停。數位錄音與 MAIN 在 100 BPM 都只辨識到前五下小鼓。在數位錄音的第 17～19 秒，每個一秒視窗的峰值不超過 2 個 16-bit PCM 單位，與應繼續有鼓點的譜面不符。預期後三下小鼓在 16.2、17.4、18.6 秒，八小節應在 19.2 秒結束。約 16 秒後只剩尾音，符合原始 120 BPM 八小節的長度。五個 MIDI clip 均設為 ticks timebase，專案檔中的長度皆為 768,000 samples。這是對剪輯邊界的初步推測，單次硬體對照無法確定程式根因。

**結論**：停播改速後重新起播的節拍跟隨通過；100 BPM 下完整八小節的伴奏播放未通過。兩遍在已播出的副歌段均有一次銅鈸。[100 BPM 量測](tempo-b-result.json) · [100 BPM 數位伴奏](tempo-b.wav) · [100 BPM MAIN 混音](tempo-b-main.wav)。

**PC1X 跟彈：未測。** 演奏者確認兩遍伴奏播放期間均未跟彈，只在伴奏結束後隨手按了幾下琴鍵。CH2 電平僅作原始紀錄。小鼓計數可從 SoundCraft 送往 Model 12 前的獨立數位伴奏驗證。

## 修正後重測與上游分工

同一份 S-MU2000 八小節伴奏，48 kHz，Model 12 由歌頭送 Clock，經 DIN → UM-ONE 跟播。100 BPM 的數位與 MAIN 兩路均從 5/8 恢復為 8/8，MAIN 每拍 600.23 ms，最後的踩鈸位於副歌銅鈸後 9.303 秒。120 BPM 對照兩路均為 8/8，每拍 499.86 ms，最後的踩鈸位於副歌銅鈸後 7.748 秒。兩遍的副歌銅鈸各響一次且正常跟停。100 BPM 首次補錄只取得數位聲音，表列採用完整的雙路重錄。[100 BPM 雙路量測](../band-tempo-1669-clip-fix/tempo-b-result.json) · [120 BPM 雙路量測](../band-tempo-1669-clip-fix/tempo-120-result.json)

回歸測試確認起音按拍點放慢，但原本 768,000 samples 的 clip 邊界截掉了第 16.2、17.4、18.6 秒的小鼓。修正後 120 與 100 BPM 的八小節邊界分別為 16.000 與 19.200 秒。以實體 MIDI 迴路重播本次擷取的兩組 Clock，數位輸出再次各有八下小鼓、一次副歌銅鈸。[100 BPM 迴路](../band-tempo-1669-release-check/tempo-b-result.json) · [120 BPM 迴路](../band-tempo-1669-release-check/tempo-120-result.json)

在上游 main 的 85623f2 執行一般改速命令亦重現，與 MAIN 混音輸出或 PC1X 的操作無關。一般改速由現有的 [#785](https://github.com/storytold/soundcraft/pull/785) 處理，可直接合入 main；我們的 [#1690](https://github.com/storytold/soundcraft/issues/1690) 提供重現證據。[#1669](https://github.com/storytold/soundcraft/pull/1669) 只修正外部 Clock 的暫時播放格線，保留專案中原來的速度與剪輯邊界。PC1X 跟彈仍列為未測。

同一個引擎測試呼叫 `event.tempo` 並檢查八個預期起音的合成器輸出。main 的 `85623f28` 在 120 BPM 得到 8/8、100 BPM 得到 5/8。直接在 #785 的 `a278c26f` 加入同一個測試，兩個速度都有 8/8，八小節邊界、復原和重做也通過。#785 此次只跑這一個針對性測試。#1669 的外部 Clock 修正已推至 `5b1418a`，四個相關 crate 的 Windows 函式庫測試合計 1,213 通過、5 預設忽略、1 項影片路徑測試失敗；同一個影片測試在未修改的 main 也失敗。格式檢查及四個 crate 的 all-targets Clippy 已完成。[main 回歸測試補丁](../band-tempo-1669-clip-fix/manual-tempo-probe.patch) · [main 重現紀錄](../../../tmp/1669-eight-bars/main-red.txt) · [#785 驗證紀錄](../../../tmp/1669-eight-bars/785-result.txt)
