# Model 12 退出 STORAGE 後的 ASIO 回呼與 MTC 重新定位

2026-11-22，本機環境診斷。暫停 G-11 效能驗收。以下保留觀測值；三次退出 STORAGE 的資料只用來診斷裝置恢復，不能用來評估一般播放效能。

## 量測環境

| 項目 | 本機讀值與來源 |
|---|---|
| 韌體與歌曲 | 操作員讀值 **1.50 0103**，先前為 1.30 0088。本輪進出 STORAGE 都是 1.50，歌曲 48 kHz／24-bit；USB MULTI，電腦 1/2 回到 CH9/10，OUTPUT DELAY 停用。 |
| Windows 與工作階段 | Windows 11，26H2，build 26300.9974；高效能電源計畫（`8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c`）。操作員在本機，量測期間未發現 RDP 或 Chrome 遠端桌面連線。 |
| 驅動 | TASCAM Windows Driver and Settings Panel **2.20**，官方列出的發行日期為 **2025-06-25**，本機安裝於 2026-11-18。Windows 載入 TEAC 簽署的 **14.30.55.883**，INF 日期 **2024-07-04**。SetupAPI 記錄顯示安裝器選用 `win10/x64/avs`；已載入的 INF、SYS 分別與套件內該路徑的兩個檔案 SHA-256 相同。套件另附不同版本 INF。 |
| 驅動實報 | Model Mixer ASIO 原生雙向串流：48,000 Hz、256 取樣、packed I24，輸入／輸出延遲回報 304／728 取樣。由 ASIO 串流讀回。單塊名義週期 5.333 ms。 |
| 軟體與路徑 | STORAGE 量測使用本機整合版 `f561a57a`（#1662、#1663、#1669 加 #1634 的 I24 支援）。同一程序、同一雙向串流的輸出 1 與輸入 9，取 ASIO buffer-switch 內的 Windows QPC 時間戳與裝置取樣位置。 |
| 環境事件 | STORAGE 期間 Windows 預設播放端點改變，三輪各有一個 CPU 觀測值超過 75%（76.3%、75.1%、76.6%）。現有證據不能從中指定根因。 |

[驅動、套件與雜湊清單](runs/asio-environment-inventory.json) · [TASCAM 官方下載清單](https://www.tascam.eu/en/downloads/model12) · [TASCAM 韌體變更紀錄](https://cf.tascam.com/wp-content/uploads/downloads/products/tascam/model_12/e_model12_rn_vl.txt)

## STORAGE 回呼間隔直方圖（實機）

每輪取第一至最後一個實收 MTC quarter-frame 的完整視窗，約 8 秒，以相鄰回呼計數。下表的「其他」涵蓋兩個列出區間以外的全部間隔。

| 觀測窗 | 間隔數 | 4 至 <7 ms | 240 至 <260 ms | 其他 | 最小／中位／最大（ms） |
|---|---:|---:|---:|---:|---|
| 進 STORAGE 前 | 1,497 | 1,497 | 0 | 0 | 4.859／5.018／6.136 |
| 第一次退出後 | 30 | 0 | 30 | 0 | 250.284／251.266／252.446 |
| 第二次退出後 | 31 | 0 | 31 | 0 | 250.247／251.250／253.022 |
| 第三次退出後 | 30 | 0 | 30 | 0 | 250.117／251.322／252.610 |

退出後三個視窗內的 **91/91** 個間隔均在 250–254 ms。各回呼序號連續，取樣位置每次仍只增加 256；若以 48 kHz 正常推進，251 ms 應推進約 12,048 取樣。基準視窗的平均間隔是 5.333 ms。這項量測辨識出回呼交付節奏異常，尚不能分開歸因於應用程式、驅動或 USB 裝置恢復。[原始直方圖與取樣位置](runs/asio-environment-histogram.json) · [擷取資料](runs/h3b-model12-01/)

## upstream main 對照

獨立播放器在三次退出 STORAGE 後，於同一程序和同一驅動實例重建雙向 ASIO 串流，三次都回到平均 5.33 ms。[重開前後直方圖與恢復操作](ASIO-storage-reopen.zh-TW.md)

獨立的 Steinberg SDK 播放器直接載入 TASCAM 驅動，在沒有 SoundCraft、#1634、CPAL 或 asio-sys 的條件下也完成三輪並重現異常。[三種播放程式與原生回呼比較](ASIO-storage-independent.zh-TW.md)

後續以 main 只合入 #1634 完成三輪實機對照。該版本能開啟同一個原生裝置，退出 STORAGE 後三輪均重現約 251 ms 的回呼節奏。[直方圖與兩版本比較](ASIO-storage-main-I24.zh-TW.md)

以當時 upstream main `85623f28f99a9a788123f0f6b48829f95f07962f` 建置，啟用 ASIO，沿用相同的底層回呼記錄工具。SoundCraft 主程式使用該提交原始碼。透過正常音訊設定指定同一 ASIO 輸入／輸出、48 kHz、256 取樣。主程式記錄 `unsupported device sample format I24; using a silent clock`；10 秒內原生串流數為 0，裝置狀態回報靜音、0 聲道、無實際 buffer。**main 的 ASIO 間隔無法量測**，因此「main 正常、PR 異常」及「兩者同樣異常」都缺少同條件對照。暫不歸因或修改產品程式。[裝置設定](runs/storage-main-85623f28-01/configuration.json) · [應用程式紀錄](runs/storage-main-85623f28-01/application.log) · [10 秒結果](runs/storage-main-85623f28-01/result.json) · [建置版本](audio/build/85623f28-build.json)

## 其他量測值

| 同一台裝置、同一版 1.50 韌體 | 進 STORAGE 前 | 三次退出後，依次列出 |
|---|---:|---|
| ASIO 輸出 1 的 A4 相對 DIN 時間軸 | −14.780 ms | 三輪 PCM 均不足以量測 |
| CH9 回送的 A4 相對 DIN 時間軸 | +5.478 ms | 三輪 PCM 均不足以量測 |
| 預期 A4 前後各一秒的回呼數 | 375 | 8、8、8 |
| DIN 實收 quarter-frame 數 | 960 | 960、960、960 |
| DIN 解碼參考時刻的極差 | 0.572 ms | 0.553、0.597、0.628 ms |

歷史資料也來自實機，但條件有變。韌體 1.30 的共享音訊測試中，A4 進 STORAGE 前為 +3.810 ms，退出後為 +3.321、+3.183、+3.181 ms；1.50 的原廠 ASIO 結果見上表。另一項 1.30 的 SD 測試量第 5 秒的鋼琴 A4，三次為 +13.5、+51.5、+55.5 ms；1.50 的 H-4b 量起播後 0.25 秒的編碼脈衝，CH9 為 +215.732、+216.548、+217.523 ms。兩版間同時改了音訊路徑、軟體或刺激信號，沒有單獨估出韌體造成的延遲差。離線重播只用來驗證跳轉行為，未拿來計算實機延遲。[歷史 STORAGE 摘要](../g11-hardware/ROUND4-ACCEPTANCE.zh-TW.md) · [歷史 SD 量測](../g11-hardware/h-mtc-sd-phase-20261121/REPORT.zh-TW.md)

## #1663 重新定位與 Known limitations

三次 H-4b 皆在第一次 STORAGE **之前**完成。每輪重新定位都發生在第一個 quarter-frame 後約 1.15–1.33 秒（由相鄰狀態查詢夾出）。三輪各有 13,287、13,237、13,300 個原生回呼間隔，最長各為 6.499、6.228、6.293 ms；39,824 個間隔中，超過兩個緩衝週期者為 0。三輪的定位均可排除本案約 251 ms 的回呼停滯。[逐輪原始統計](runs/h4b-before-storage-cadence.json)

起播保護已確認的停止定位點；追隨期間若播放位置與 master 相差超過一格並持續至少一秒，SoundCraft 重新定位到 master。這裡的「一秒」是偏差持續時間。離線將首輪的 301 筆 quarter-frame、478 個回呼時間重播到原 #1663，排入四個短 PCM 標記，算得一次重新定位、三個起音。第三個標記完全位於跳過的區間，略過符合採用的規則。原始測試假設四個起音必須全播，其失敗紀錄保留作為行為證據。此結果未單獨量出初始相位差各來源的占比。[離線重播結果](software-h4b/result.json) · [定位判定程式](integrated-mtc/crates/playback/src/callback.rs)

**Known limitation — 持續中的 MIDI 音符。** #1663 能恢復先前的控制器值；現有 MIDI 音符排程只在 note-on 落入當前區塊時送出。定位到已開始、尚未結束的長音中間，SoundCraft 不會重新觸發該音。依決定列為限制，保留現行 master 優先規則。Pro Tools Reference Guide 2026.4 印刷頁 1043 的 Note Chasing 說明，新建 MIDI／Instrument 軌預設啟用此功能。[音符與控制器排程](integrated-mtc/crates/mix/src/midi.rs) · [Avid 手冊，第 1043 頁](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf#page=1145)
