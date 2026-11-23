# 樂團排練驗收 · 副歌重來一次

2026-11-22，SoundCraft #1669，commit `67b3e50a75a071c245ffdacfaf980d2ee0cf0e2e`。八小節，120 BPM，4/4。貝斯使用 S‑MU2000 VST3，四條鼓軌用 MIDI 觸發 S‑MU2000 音色取樣。唯一的 Crash Note On 在 tick 15360（960 PPQ），即第 5 小節第一拍。

Model 12 送 Continue、Clock、Stop，SoundCraft 從 DIN OUT 經 UM‑ONE 跟隨。同步側錄 Model 12 的 USB MIDI 與 UM‑ONE。SoundCraft 數位輸出經監聽程式送至 Model 12 ASIO 9/10，另從 USB 11/12 錄下 MAIN 混音，兩路皆為 48 kHz。機上歌曲為 48/24。

| 錄次 | Continue 前最後 SPP | 停止中位置（48 kHz） | 本體與 DIN 各自收到的 Clock 數 | 銅鈸次數（數位／MAIN） | MAIN 後續伴奏與參考的相關係數 |
|---|---:|---:|---:|---:|---:|
| [面板定位](panel-first-result.json) | 65 | 390000（8.125 秒） | 211 | 0／0 | 0.997 |
| [面板再次送出定位](exact-second-result.json) | 65 | 390000（8.125 秒） | 266 | 0／0 | 0.997 |
| [精確起點](exact-final-result.json) | 64 | 384000（8.000 秒） | 161 | 1／1 | 0.997 |

第二次先收到 64，接著 Model 12 在 Continue 前送出 65，因此按 8.125 秒計入。最後一次由電腦經 Model 12 USB MIDI → DIN OUT → UM‑ONE 單送定位 64。其後由本體按鍵起停並提供全部 161 個時鐘脈衝。兩個起點皆跟隨本體約 120 BPM。

用銅鈸取樣的起音視窗在整段回錄搜尋，正規化相關係數高於 0.90 為命中，另核對後續伴奏確實存在。8.000 秒的銅鈸是數位回錄的第一個起音；MAIN 銅鈸相關係數 0.9999。8.125 秒兩次 MAIN 最高銅鈸相關係數分別為 0.2004、0.1920。驗收範圍是 Continue 邊界的觸發次數與後續播放，喇叭至聆聽位置的聲學延遲未量測。

**結果：通過。** [8.000 秒 MAIN 錄音](exact-final-main.wav) · [8.125 秒 MAIN 錄音](panel-first-main.wav)

## 第二個樂團情境

[Model 12 從 120 改為 100 BPM，S-MU2000 伴奏跟隨](../band-tempo-20261122-004905/REPORT.zh-TW.md)。初測 100 BPM 時副歌缺少最後三下小鼓；修正後兩個速度的數位與 MAIN 回錄都收到八下。PC1X 跟彈未測。另見[樂團情境自動驗收與副歌變速的拍點量測](../band-overnight-20261122-fixed/REPORT.zh-TW.md)。
