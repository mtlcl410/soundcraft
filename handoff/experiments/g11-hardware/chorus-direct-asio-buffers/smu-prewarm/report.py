from pathlib import Path
import json
w=Path(__file__).resolve().parent;d=w.parent
rows=json.loads((w/'final-results.json').read_bytes())
def span(vals):return '、'.join(f'{v:.3f}' for v in vals)
table='| ASIO 取樣 | 區塊預算 | 原安裝版首次 process | 預熱後首次 process | 預熱後整個回呼 |\n|---:|---:|---:|---:|---:|'
for size,old in [(128,10.040),(64,6.778)]:
 sub=[r for r in rows if r['buffer']==size]
 table+=f"\n| {size} | {sub[0]['budget']:.3f} ms | {old:.3f} ms | {span(r['plugin_ms'] for r in sub)} ms | {span(r['callback_ms'] for r in sub)} ms |"
lines=['# S-MU2000 在播放前預熱','',table,'',
'每個預熱後的數字代表重新啟動 SoundCraft 並重新開啟同一份專案後的第一次有聲回呼。原安裝版數字取自前輪同一路徑的硬體紀錄。計時包含 Windows 排程，不能當作所有演出環境的最壞時間。',
'','## 為何第一個區塊特別慢','',
'以與安裝版相同的 317b8fe 原始碼編譯 Windows x64 VST3。在 128 取樣的分段診斷中，48 kHz 專案的一次外掛呼叫處理 140 個專案取樣，共 10.639 ms。合成填充占 10.613 ms，其中音訊執行緒編譯 SH‑2 韌體指令占 7.756 ms，重建效果器 MEG 程式占 0.198 ms。初始 XG 參數讀取為 0.004 ms，延後還原專案狀態為 0。本機的啟動快取還原了模擬器狀態，但沒有這些已編譯指令。分段數字互有包含，不能相加。另一次同編譯器重建的舊版量到首次 process 10.943 ms。',
'','## 修改與回歸','',
'在 S-MU2000 的 VST3 啟用與專案狀態還原時，由控制執行緒準備音源。用共享唯讀 ROM 的暫時音源副本探索閒置和收、放音符時經過的韌體程式區塊，在正式音源上提前編譯那些位址。效果器程式穩定且因還原而需要重建時也先準備好；遇到韌體正改寫效果器仍沿用既有的等待規則。正式音源預熱期間前進零個取樣，也收不到副本的試音。另移除 setProcessing 在音訊執行緒同步開關記錄檔的動作。',
'',
'先將 ASIO 預算檢查套回舊版，128、64 都失敗。只預熱開機閒置狀態的試作在 128 仍花 7.336 ms。改用專案狀態並涵蓋音符處理後降到 2.827 ms。再將效果器提前準備後，兩次試作為 1.669、1.655 ms。表格列的是最後保留的版本。'+
' 另用原廠 vst3probe 載入專案保存的貝斯音色，播放兩個音並放鍵。前後兩份 48 kHz 立體聲 PCM 的 55,199 個取樣框逐位相同。',
'','## Model 12 驗收','',
'專案 Back to the Chorus 的 SHA‑256 為 992c9ea2e252052261f326a03be545683f3bf9a59d1db5ab166a0acc1d5a7071。Model 12 使用 44.1 kHz，直接由原廠 ASIO 9/10 輸出，從 MAIN USB 11/12 回錄。實體 MIDI 經 Model 12 的 DIN OUT 接回 UM‑ONE。每次起播均比對 SPP、Continue、144 個 Clock、Stop，以及實收音訊回呼的尺寸。驗收以 MAIN 錄音與銅鈸樣本的相關值大於 0.90 計數，並獨立檢查後續伴奏。',
'',
f"8.000 秒的 {sum(r['exact_once'] for r in rows)} 次均只辨認到一個銅鈸。8.125 秒的 {sum(r['late_no_replay'] for r in rows)} 次均未補播。後續音符最低相關值 {min(r['after_note_correlation_min'] for r in rows):.4f}。兩路擷取序號都連續。原有波形檢查共標記 {sum(r['waveform_steps_over_32'] for r in rows)} 段錄音有超過 32 個 PCM 單位的相鄰殘差變化，偵測到 {sum(r['detected_drop_windows'] for r in rows)} 個低電平視窗。聽感留待本人盲聽。",'',
'![第一次處理音訊的時間與緩衝預算](first-process.png)','',
'[S-MU2000 修正](s-mu2000-prewarm.patch) · [舊版失敗紀錄](regression-before.txt) · [分段計時](../prewarm-diag-c/cold.txt) · [冷啟動與音符驗收](final-results.json) · [PCM 比對](bass-null-test.json) · [回歸檢查](verify.py) · [硬體驗收程式](audio_check.py)']
(w/'REPORT.zh-TW.md').write_text('\n'.join(lines)+'\n',encoding='utf8')

