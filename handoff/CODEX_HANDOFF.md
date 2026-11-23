# G-11 本機驗收交接 · 2026-11-23（台灣時間）

請先讀這頁。本次為交接快照。工作站最後的兩小時實測已於 14:23:51 收尾。後續是否修改或發布產品由接手者與使用者決定。目前的產品候選包含尚在驗證的行為。

## GitHub 與本機版本

| 上游 PR | GitHub 狀態、head（交接時） | 對應 WIP 版本 |
|---|---|---|
| [#1662 Beat Clock 輸出](https://github.com/storytold/soundcraft/pull/1662) | Open / Draft，`8fd150681cb7ed2497887fdb784e82e1c399bafa` | `wip/1662-clock-output`，`c7e2d50f363ea90387965eb89e71c74ae06c6f66`。已待命的零起點送 Start；保留既有埠中途接入及取樣捨入語意。此層播放測試 175 通過、1 略過。 |
| [#1663 MTC 產生／追隨](https://github.com/storytold/soundcraft/pull/1663) | Open / Draft，`bab993121ab583b5916272907b1230e8a4f4bd91` | `wip/1663-mtc-device-clock`，`1db8bdb65c156d845b3b2dec0c1fb28865659a2c`。以已知音訊取樣速差驗證生成的時間碼。此層播放測試 227 通過、3 略過。 |
| [#1669 外部 Beat Clock 跟隨](https://github.com/storytold/soundcraft/pull/1669) | Open / Draft，`33dfa5f5d3b6afd33bf0b6b8df57b755d662a8fa` | 主交接分支 `wip/1669-stop-extra-f8`。產品修正 `f533e1db`；含最後一項回歸測試 `1af5815b6a65635d5327dc7c53b8eea937ecd4d7`；其後為交接資料。 |
| 本機硬體驗收版 | G-11 整合、#1634 I24 路徑、量測探針 | `4ed607bfd7eff6a8804fbe848680942e510ef8ca`。可在 WIP 封存歷史中取回。測試執行檔 SHA-256 與原路徑見 [build.json](hardware/overnight-evidence/stop-ordinal-4ed607bf-two-hours/build.json)。 |

三支 PR 的 GitHub base 欄位都是 main。實作整合順序為 #1662 → #1663 → #1669。交接分支與封存提交供獨立取回；不要把實機探針或封存歷史整包合入產品 PR。

## H-10 驗收

Model 12 韌體 1.50 0103、原廠 ASIO 48 kHz / 256 samples、UM-ONE、兩段實體 DIN，中間使用獨立 Windows 虛擬埠轉送，以避免同名輸入、輸出構成回授。採用 120 BPM，啟用 Beat Clock 跟隨、Beat Clock 輸出與 30 fps MTC 產生。預設輸出補償開啟，手動偏移 0。兩小時為實際經過時間。環境判定有效。[實機報告](hardware/H10-時鐘速差與起停邊界.zh-TW.md) · [嚴格測試輸出](hardware/overnight-evidence/stop-ordinal-4ed607bf-two-hours-strict.log)

| 條件 | 方法與最新結果 | 判定 |
|---|---|---|
| 無失鎖 | 讀工作站鎖定狀態與累計 dropout；0 次 | 通過 |
| 無少送或多送 F8 | 分別計算來源、實體輸入、轉送後輸入與實體輸出的 F8；四者皆 345,600。前次實體輸出 345,601。這次在 FC 後 2.329 ms 攔下序號 345600（從 0 起算），輸出 FC 後再收 0 個 F8 | 本輪通過；不同 Stop 相位仍有限制 |
| 無少送或多送 MTC quarter-frame | 外部兩小時嚴格預期 864,000，實收 864,023。片段編號無中斷，108,002 個完整地址各前進兩格，最後一組只收到索引 0～6。停止後有 full-frame 定位 | **原嚴格計數未通過，差 +23** |
| 跟隨相位未持續增長 | 取首、末各十分鐘 Locked 狀態，兩窗各 597 筆。帶符號誤差中位數 −2.917 → −2.729 ms，絕對誤差 p95 3.896 → 3.625 ms | 這兩窗未見劣化。這是主機估計相位 |
| 記憶體未增長 | 程序 private bytes 的首末十分鐘中位數 514,347,008 → 515,956,736（+1,609,728 bytes）。首末單點差 +3,162,112 bytes | 嚴格零成長未達；單輪不足以判定洩漏 |
| 佇列未增長 | 輸出擷取端歷次觀察最大深度 0；輸入 relay 的深度欄位為 null，沒有相應的長度樣本 | 已觀察的輸出端通過；輸入端未驗證 |

[首末十分鐘原始彙整](H10-final-windows.json) · [逐項程式驗收摘要](hardware/overnight-evidence/stop-ordinal-4ed607bf-two-hours/stop-verdict.json) · [完整組與七片尾段](hardware/overnight-evidence/stop-ordinal-4ed607bf-two-hours/qf-complete-and-partial.json)。自動計數套件 5 個斷言中 4 個通過；記憶體與佇列另外列在原驗收要求中。ASIO 共記錄 1,351,039 個回呼，平均 5.333 ms、p99 6.081 ms、最大 21.323 ms。取樣位置與回呼序號連續，200–300 ms 區間 0 次。

## #1669 的候選修正

舊版從相同起點收到 576 個外部 F8。八次舊紀錄中七次輸出 577 個，四次在程式辨認 FC 後 3.387～4.927 ms 才交付第 577 個，其餘三次在 FC 前已送入 Windows。這兩種情況需要不同處理。[舊紀錄逐輪解碼](hardware/overnight-evidence/stop-ordinal-replay.json)

收到明確 FC 時，候選程式保存這次外部播放的最後有效脈衝位置。在原生 MIDI 埠逐筆交付前，依該輸出的 Start、SPP、Continue 與 F8 算出目的端位置，核對播放段並攔下超出來源終點的 F8。只用於零手動輸出偏移。批次內仍欠的有效脈衝照常送出，斷鐘進入 Coast 不設舊來源上限。普通播放保留原排程。

- 零起點、非零 Continue 在修前都錯送 3 個，預期 2 個。完整播放測試修後 **285 通過、3 略過**，涵蓋原生呼叫阻塞時同批送出「有效、有效、過量」的順序。[修前](hardware/overnight-evidence/stop-ordinal-red.log) · [修後](hardware/overnight-evidence/stop-ordinal-batch-green.log)
- 四個 Stop 時點分別提前 0、5、10、15 ms。補償開啟四輪均 576/576。補償關閉四輪中一輪 576/576，其餘均 577/576（輸出/輸入）；多出的三個都已在輸入 FC 前完成原生呼叫。八輪均未少送，輸出埠自己的 FC 後皆無 F8。[實機矩陣](hardware/overnight-evidence/stop-ordinal-matrix-4ed607bf.json)
- 仍需區分「總數相符」與瞬時相位。這輪實機為單一零偏移輸出，其他介面、多輸出、多種手動偏移、立即換來源及任意時點連續停啟均未獲同等實機驗證。

## 接手後的分析順序

1. 先沿用最新 7,200 秒錄檔，對齊原生 ASIO sample position、QPC、輸入 FA/FC 以及 DIN 返回的 MTC 地址。中間 110 分鐘，裝置比電腦計時多走 220.125 ms，預測多 26.415 片，觀察到多 26 片。[時鐘分窗](hardware/overnight-evidence/stop-ordinal-4ed607bf-two-hours/counter-domains.json)
2. 分別核對起播、最後完整組、最後七片和停止 full-frame。完整群組的算術解釋了封包數量；新一輪尚未完成逐組對 ASIO 取樣的殘差與首末十分鐘趨勢分析。舊分析器對非完整尾組會報錯。已保留 [尾段解碼工具](hardware/overnight-evidence/stop_ordinal_decode_groups.py)，請保留七片原始事實，勿補出假的第八片。
3. 若相對裝置取樣仍有累積偏差，先用時間戳回放建立修前失敗再檢查 #1663。若能對齊，並列外部計時與音訊時鐘兩種結果，把驗收基準交由維護者決定。保留 864,000 原門檻。
4. 若使用者要求驗證記憶體零成長，需追蹤配置來源或比較重複長測的平臺。需要輸入佇列的大小時，先補採集工具的觀測，再決定是否重做硬體測試。

## 試過的取捨及環境限制

- 全程強制每個輸出 F8 等到同序號輸入時，離線重播顯示有 365 個脈衝會被延後，最差多等 45.262 ms。故採 Stop 邊界的限縮修正。
- 關閉補償能縮短送出 FC 的延遲，但會提早正常 F8 的送出時間，無法撤回已交付的訊息。冷接入與歌頭預先待命必須區分；放寬所有起播窗口曾破壞取樣捨入的既有測試。
- STORAGE 退出後約 251 ms 的舊串流回呼也可由獨立 ASIO 播放器重現。工作站僅在已停止播放與錄音時重建串流的研究有獨立報告。[ASIO 恢復報告](hardware/ASIO-storage-idle-recovery.zh-TW.md)
- 先前 256 samples 的 12 次中 1 次波形偏差、64 samples 的短暫近靜音事件，與這輪長測的 Clock 計數分別追蹤。MTC 快轉定位時跨過的音遵循外部主機位置；既有驗證與門檻請見 [硬體驗收索引](hardware/REPORT.zh-TW.md)。

## 檔案與還原

原報告位於 `E:/soundcraft/compatibility-audit/g11-hw-acceptance/H10-時鐘速差與起停邊界.zh-TW.md`。同名報告、引用的小檔案、腳本與探針均放在 [hardware/](hardware/)。最新長測原檔目錄為 `E:/soundcraft/compatibility-audit/g11-hw-acceptance/overnight-evidence/stop-ordinal-4ed607bf-two-hours/`。前次長測在同層 `reboot-0823-two-hours/`。最新原生錄檔 `driver/epoch-0.bin` 為 2,820,969,432 bytes。[本機檔案路徑、大小與 SHA-256](LOCAL_RECORDINGS.json)。重作逐組取樣殘差分析需要這些原始檔；只讀交接結論與逐輪結果可以完全在 GitHub 完成。

軟體工作樹為 `E:/soundcraft/compatibility-audit/g11-hw-acceptance/stop-ordinal-local`，對應實機工作樹為同層 `stop-ordinal-hardware`。腳本按原實驗目錄布局尋找依賴，部分會控制實體設備或重建本機暫存設定；離線分析優先使用已存的驗收資料。


## 封存與恢復

- [完整盤點](inventory/BEFORE.json) 按 Git 儲存庫列出每棵 worktree、HEAD、branch、各檔案的 Git 狀態、stash，以及原樣執行 `git log --branches --not --remotes --oneline` 的結果。這台機器的 G-11 共用庫沒有 remote-tracking refs；該指令中的 417 筆包含已公開提交。[對照遠端 refs 後的候選清單與限制](inventory/LOCAL_ONLY_CANDIDATES.json)。不屬於 G-11 的工作只列盤點。
- [G-11 封存索引](inventory/G11_REFS.json) 列出原工作樹位置、原 HEAD、原分支與可還原的 snapshot SHA。要取回紅測、歷史探針或合併中的實驗，在 fork 的 clone 執行 `git fetch origin wip/g11-worktree-archive`，再以 `git worktree add --detach ../g11-inspect <snapshot-SHA>` 開獨立目錄。封存分支的歷史只用於取回快照。產品開發從上表三個對應分支繼續。
- 暫存區與工作檔不同的實驗另存 [index-states](inventory/index-states/)，含 stage 編號、Git blob 與尚未解決的衝突兩側。個別檔案以 `git cat-file blob <SHA>` 或該目錄的 blobs 讀取。原來的 stash 也可由封存分支取得，SHA 見索引，以 `git stash show -p <SHA>` 查看。嵌套的 env-main-control 以 gitlink 指向其工作樹 SHA。
- [歷次實驗](experiments/) 保存本機量測腳本和相關報告。[原有 Git blobs](inventory/EXISTING_EXPERIMENT_BLOBS.json) 列出可按內容編號取回的重複來源。測試資料中的舊指令與發布腳本僅作歷史記錄。大型錄檔留在原機；其他專案的程式與修改保留於其原儲存庫。

最終核對涵蓋 25 個專案儲存庫、235 棵既有工作樹。141 棵 G-11 工作樹目前乾淨；其中 57 棵原有未提交內容。其餘 94 棵依原狀保留，其中 31 棵仍有先前的修改。另在僅從 GitHub 抓取的獨立儲存庫確認，封存歷史可取回索引裡全部 168 個不同版本。原 G-11 共用庫的 417 筆 log 中，有 145 筆在交接前 fork 與上游公布的各 branch 歷史均找不到；109 筆在 G-11 封存內，其餘 36 筆屬其他工作。[盤點摘要](inventory/README.md) · [逐工作樹核對](inventory/AFTER.json)
