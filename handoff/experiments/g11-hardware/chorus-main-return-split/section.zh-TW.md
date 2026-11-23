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
