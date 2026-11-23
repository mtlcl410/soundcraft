# G-11 最後一輪驗收

| PR | 審查起點 | 回歸證據 |
| --- | --- | --- |
| #1662 | `168a1810` | [停止定位舊版](evidence/F62-5-red.log)、[時間警告／恢復舊版](evidence/route62-red.log)、[同名埠舊版](evidence/ports-red-observed.log)、[偏好設定舊版](evidence/f62-prefs-red.log)、[整合版驗證](evidence/1662-7ff81296/results.json) |
| #1663 | `14030820` | [下移的 MTC 測試](evidence/F63-owners-unfixed.log)、[交錯封包與跨日舊版](evidence/route63-red-verified.log)、[專案設定舊版](evidence/f63-prefs-red.log) |
| #1669 | `c093aedb` | [上一輪逐情境結果](../g11-dj-audit/REPORT.zh-TW.md) |

## #1662

停止中跳到第 7 個十六分音符，舊版只送 Stop。修正後送出一次 `F2 07 00`，重複定位、一般停播與循環回到起點的行為亦有回歸測試。時間戳異常的警告只對有使用補償的路由出現。自動開埠的次數耗盡後，一分鐘內最多再查兩次裝置是否存在。

同名輸出的兩組校正以模擬端點測試；實機驗證沿用先前 Model 12／UM-ONE 的結果。設定復原測試涵蓋單欄損壞與可見提示。Notes/Controllers 控制項的不可用狀態使用無障礙樹驗證。

## #1663

舊版在 30 fps 跨午夜時，時序由 3,974,399,600 samples 倒跳至 −172,797,200；相鄰反向定位也落在錯誤日期。將 F8 插進 MTC 後，舊版遺失了定位。這些是軟體接收器／產生器測試。

| 在 `14030820` 實際跑到的舊版失敗 | 觀察值 | 驗收值 |
| --- | --- | --- |
| 工作階段由 01:00:00:00 起算，輸入五秒 pre-roll | 被拒為早於工作階段起點 | 接受五秒的長度 |
| 48 kHz／29.97 非 drop-frame 的第 2 格定位 | −1 sample | 0 |
| 產生器從偶數格的第一個整數 sample 起播 | 只有 full-frame，缺第一個 quarter-frame | 兩者依序送出 |
| 停止時把外部 offset 加一秒 | 480,000 samples | 528,000 samples |
| Record 已排隊才切到 Online | 狀態列空白 | 與手動錄音相同的拒絕原因 |
| 維持絕對時碼且啟用 Automation Follows Edit | 4 個 automation 點都沒移動 | 每個點移動 +86,400,000 samples |

## 另案

Windows 的影片重新連結測試由 #1536 追蹤。選取 engine 的 Clippy 在既有 `autosave.rs:481` 會報 `unused_mut`。整個設定檔的通用損壞復原屬 main；本輪按個別 PR 新增的同步欄位驗證。

## 本輪驗證進度

- #1662 已發佈至原草稿，提交為 `7ff81296df6d36a565c4636d75da682d52bc5423`。Playback 160 通過／1 忽略，UI 361 通過，應用程式 56 通過，Clippy 與格式通過。GitHub 四個工作流程都需要維護者核准。本層的 Open questions 已清空。[原 PR 驗證留言](https://github.com/storytold/soundcraft/pull/1662#issuecomment-7074204227)
- #1663 的完整 UI 測試在中間版本發現第 256 個校正欄位用滿後，新選擇的零偏移輸出會被拒絕。修正保留 256 筆校正及獨立 MTC 輸出的裝置 ID。最新 head 另行驗證。
- #1663 已推至草稿 head `671b6672f8bb160292243bd2613b6710d7bacf81`。Playback 203、UI 386、engine 450、應用程式 58 項通過，共 1,097 項。Engine 的 Windows 影片重新連結測試失敗（#1536）。一般測試略過兩項，另行執行的四種 MTC 幀率十分鐘抖動測試通過。Playback／UI 的 Clippy、格式通過。四個 GitHub Actions 工作流程仍待維護者核准。已在原 PR 送出一次指定的單行指令，機器人確認觸發。[回歸紀錄](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074474906) · [審查狀態](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074475449)

### #1663 正式審查的重現紀錄

CodeRabbit 已正式審查 `671b6672`。共 10 則行內意見、14 則補充意見與 1 則文件意見。以下均為軟體回歸；本輪沒有新增實機錄音。[原審查](https://github.com/storytold/soundcraft/pull/1663#pullrequestreview-6010501117)

| 路徑 | 修正前觀察 | 驗證方式 |
| --- | --- | --- |
| 48 → 96 kHz 切換 | 已渲染的舊資料剩 424 格，48 kHz 裝置提前播完 | 在真實 callback 分兩次取 PCM，逐格核對舊音訊和新靜音的邊界，也核對輸出的取樣率。[失敗紀錄](evidence/cr63-red-retained_audio_uses.log) |
| 停止中定位且有輸入監聽 | 時碼發佈位置是 41,576，游標是 42,000 samples | 保留監聽緩衝，核對回呼發佈的播放位置與定位起點。[失敗紀錄](evidence/cr63-red-a_stopped_locate_while.log) |
| Online 與錄音命令交錯 | 拒絕錄音後，MIDI 的錄音待命仍有效 | 在 callback 讀完音符後才開啟 Online，拒絕的音符對錄音端保持不可見，下一次正常錄音只保留新音符。[失敗紀錄](evidence/cr63-red-rejected_online_recording.log) |
| 舊版與新版外部偏移並存 | 使用者將偏移歸零後重開，變回 160,000 samples | 透過 Session Setup 及獨立外部偏移命令分別改值，再重開專案。[失敗紀錄](evidence/cr63-red-explicitly_resetting.log) |
| 復原工作階段 | 顯示復原的專案名稱，卻蓋掉時碼偏移衝突的提示 | 從實際寫出的 autosave 檔復原，比對專案名稱與衝突說明是否同時可見。[失敗紀錄](evidence/cr63-red-recovery_status.log) |
| MIDI 輸入已連接、沒有播放引擎 | 介面進入錄音，但沒有 callback 可以收音符 | 執行 transport.record 並處理請求，核對 transport 與可操作的錯誤說明。[失敗紀錄](evidence/cr63-red-online_transition_gates.log) |

#1663 已推回原草稿 `8161383751314c94644a4d2af759347eddfbecc6`。本機 Playback 219、UI 390、Engine 451、應用程式 58，合計 1,118 項通過。Engine 另有已知的 #1536 影片重新連結失敗。一般 Playback 測試略過兩項；另手動執行四種幀率各十分鐘的抖動測試，通過。Playback 與 UI 的嚴格 Clippy、工作區格式通過。四個 GitHub Actions 工作流程均待維護者批准。CodeRabbit 已正式審查前版，25 項處理結果已公開；新 head 的自動複審因草稿而略過。[逐項結果](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074865328) · [草稿審查狀態](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7027417714)

<!-- BEGIN #1669 FINAL -->
## #1669 最終驗證

本機 Windows 驗證的提交為 `d2632db4e70b35da2a87a6f966db28733d8c2408`。

| 執行項目 | 通過 | 失敗 | 預設略過 |
|---|---:|---:|---:|
| soundcraft-mix | 104 | 0 | 0 |
| soundcraft-playback | 267 | 0 | 2 |
| soundcraft-ui-egui | 438 | 0 | 6 |
| soundcraft-engine | 486 | 1 | 0 |
| soundcraft | 61 | 0 | 0 |

clippy 通過；fmt 通過。另有 13 組指定驗證資料（部分與一般測試重疊），包括六項獨立執行的 ignored 長測。[每份測試輸出](evidence/1669-d2632db4/results.json)

共 20 首、31,264 個八分音符均一次起音且波形與尾音完整。排除事先指定的轉場與成組封包後，28,684 個八分音符的絕對誤差 p99.9 為 3.479 ms。含成組封包時為 34.292 ms；成組區相對到達時間的 p99.9 為 34.271 ms。±8% 連續推速峰值 3.6458 ms；緩慢漂移誤觸 0 次。八小時抖動峰值 130 samples。近門檻 120 組、真正煞車 32 組、穩定極慢時脈 6 組以及成組大幅減速 16 組都通過。成組減速最大到線延遲 166.667 ms，扣除線路等待後的最大絕對誤差 0.000 ms。

六小時 tempo history 的峰值事件數（有上限／無上限）為 512／5193，程序尖峰記憶體 14.2 MiB／14.2 MiB，末段發布 p95 為 21.300／109.800 µs。錄音範圍所需事件保留。大緩衝慢速切換，第一個反拍／第一拍最差為 +86.083／+83.646 ms。

[逐個八分音符的有號偏差](evidence/1669-d2632db4/all-eighths.csv) · [逐音分解封包時間](evidence/1669-d2632db4/packed-components.csv) · [逐案量測與可解包資料](evidence/1669-d2632db4/evidence-comment.md) · [測試與記憶體原始結果](evidence/1669-d2632db4/profiles.json) · [逐 crate、Clippy、格式](evidence/1669-d2632db4/results.json) · [六小時前後對照](evidence/1669-d2632db4/review-metrics.json) · [先前 38 項情境](../g11-dj-audit/original38/RESULTS-38.zh-TW.md)

實機沿用 Model 12 → UM-ONE 與 S-MU2000 伴奏，8.000 秒銅鈸一次，8.125 秒不補播，100 與 120 BPM 兩遍 MAIN 都有八下小鼓；本輪 DJ 壓力測試為模擬時脈與實際 PCM 渲染。Open questions 保留 EXT 快捷鍵、慢速失鐘政策、Setup 選單命名、MTC chase 是否採用輸入埠 offset。C-7 閒置對照的版號、主機負載和每次執行狀態均獨立記錄：[追蹤紀錄](evidence/c7-idle-comparison.json)。

[煞車舊版逐音](evidence/dj-brake-old-attacks.csv) · [範圍快取原始失敗](evidence/F69-2-red-isolated.log) · [loop 與 held-note 回退對照](evidence/f69-loop-noteoff-red.log) · [256+256 設定遷移回歸](evidence/registry-union-red.log)
已推回原草稿。GitHub 的 CI、Nix、ast-grep 與 SonarCloud 均為 action_required，需維護者核准。C-7 以相同工作負載另測 0／2／6 個 inserts：無建置但有桌面負載時，每 1,500 個區塊各超時 0／0／1 次；啟動前主機 CPU 為 22.1／17.8／19.5%。嚴格閒置對照另行記錄。[公開驗證留言](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7074979119) · [桌面負載對照](evidence/c7-desktop-comparison.json)
<!-- END #1669 FINAL -->

本層已推送至原草稿。四個 GitHub Actions 工作流程均需維護者核准。[最終驗證與 294 組逐音資料](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7074979119) · [150 軌桌面對照](evidence/C7-desktop-reference.md)。

[C-7 嚴格閒置量測與判讀](evidence/C7-idle-reference.md) 會在三組達到既定主機條件後自動更新。

<!-- BEGIN G11 POST-VERIFY -->
## 最後複核 R-1 至 R-6

| PR | 最新提交 | 通過 | 失敗 | 預設略過 | 驗證 |
|---|---|---:|---:|---:|---|
| #1662 | `56169122530ecdcb6d328293888cbc82caf6e0c3` | 590 | 0 | 1 | [公開驗證](https://github.com/storytold/soundcraft/pull/1662#issuecomment-7077795003) · [本機逐項輸出](evidence/1662-56169122/results.json) |
| #1663 | `e877e96f10cc19c15079975761eb2c724f29a16e` | 1118 | 1 | 2 | [公開驗證](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7077796021) · [本機逐項輸出](evidence/1663-e877e96f/results.json) |
| #1669 | `b68907e61816ab8ea60fb158f9c01a5259a57567` | 1357 | 1 | 8 | [公開驗證](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7077834130) · [本機逐項輸出](evidence/1669-b68907e6/results.json) |

R-1 的四筆輸出與裝置復原修正和測試已移回 #1662。舊版重現 13 個原有行為，第 14 個是交換 route ID 的負對照，確認測試能抓到送錯目的地。上移至 #1663 的合併提交與舊 MTC head 的整棵樹內容完全相同。[逐項對照](evidence/1662-56169122/r1-regressions.md)

R-2、R-4 以模擬到線時間驅動實際 48 kHz PCM。對照 96 組播放中由單顆變為成批的案例，從首個受影響的八分音符起算，修後首音最多額外晚 0.208 ms，後續最多額外晚 4.354 ms，最早比譜面提前 0.958 ms。96 組在已成批後減速的案例中，1,536 個受測起音全部落在其 F8 的到線取樣；封包延遲最多 166.667 ms。所有組寬和輪替相位均已涵蓋，兩組修後的空槽、重複和波形受損均為零。

20 首連續混音的 31,264 個八分音符均正確起音一次，尾音完整。舊版第 7,585–7,587 音扣除等封包後仍晚 +846／+642／+375 samples；修後為 −1／+1／0。第一個已排程的音（7,584）仍比網格早 15 samples，同時早於該 F8 到達 1,645 samples。這是不同的時間參考；成批區最大正向額外延遲由 +17.625 ms 變為 +0.021 ms。一般區 p99.9 為 3.479 ms，把群組納入同一比較後為 34.292 ms。300→240 BPM、2,048 取樣、50 ms 提前量，最差首反拍／首拍為 +86.500／+83.271 ms。[修正前逐音](evidence/r2-old-per-eighth.csv) · [修正後逐音](evidence/r2-new-per-eighth.csv) · [情境與證據](evidence/r2-r4-review.md)

R-3 的 EXT 點擊無 MIDI 輸入時，舊版狀態列為空字串；現在按鈕保持關閉並顯示選擇輸入的原因。R-5 的 10 個正式行內討論已解決，25 項總回覆的第 12 項已連到公開可讀的重現紀錄。R-6 已從 #1663、#1669 各自的差異移除新增的葡萄牙語譯文，保留英文 fallback 驗證與既有翻譯覆蓋檢查。[EXT 舊版失敗](evidence/verify-final/r3-ext-red.log) · [討論核對](evidence/verify-final/r5-after.json)

三支 PR 的 Open questions 均為零。EXT 暫無預設快捷鍵；Ctrl/Cmd+J 仍屬 MTC Online。快速穩定時脈失鐘門檻 150 ms，持續減速時可延長至 1.5 s，啟用 Active Sensing 時 300 ms 無 MIDI 活動會逾時。選單維持 Setup › MIDI › Sync。MTC chase 只套用工作階段的 External Timecode Offset。這一輪沒有新增 Model 12 實錄。

另案 C-7 的嚴格閒置對照現已跑完；每軌 0／2／6 個 inserts，各 1,500 個區塊中超時 0／0／1 次，三組均未失去 MTC 鎖定。此軟體渲染基準沒有實體 ASIO 輸出或回錄，無法據此判定有可聽掉音。[閒置條件、各組負載與完整紀錄](evidence/C7-idle-reference.md)

<!-- END G11 POST-VERIFY -->
