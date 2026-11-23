"""Append evidence only after all eight qualified physical runs have closed."""
from pathlib import Path
import json, sys
here=Path(__file__).parent
sha=sys.argv[1]
rows=json.loads((here/f'stop-ordinal-matrix-{sha}.json').read_text())
assert len(rows)==8 and all(r['valid'] for r in rows)
heading='## 外部 Stop 時最後一個 Beat Clock 的原生交付'
lines=[heading,'',
'逐次以輸入、輸出各自的 Start 為第 0 號脈衝，按實際 MIDI 訊息推進序號。八輪舊資料各有 576 個來源 F8，末號均為 575。七輪送出第 576 號；當中四輪在收到 FC 後才呼叫原生輸出，晚 3.387～4.927 ms，另三輪已在 FC 前 0.081～15.154 ms 完成原生呼叫。其餘一輪恰好送齊。序號描述接收端從 Start 累計的位置，未假設每一個 F8 都有可讀取的來源識別碼。[逐輪解碼](overnight-evidence/stop-ordinal-replay.json)','',
'本機 #1669 候選在已辨認外部 Stop 時保存該次外部播放的最後有效序號。原生輸出執行緒在交付前核對該埠的 Start、SPP、Continue 所對應的位置。僅在同一播放段、零手動輸出偏移時攔下超界脈衝。明確 Stop 前照既有時間排程。斷鐘 Coast 不以先前收到的脈衝數封頂。已交給 Windows 的訊息無法撤回。','',
'本機回歸測試中，舊邏輯在零起點與非零 Continue 都交付 3 個 F8，預期為 2。新測試另以真正的播放回呼建立播放段，將原生埠停在第一個 F8 的送出呼叫內，再從輸入埠送 Stop，確認同一批次的第二個有效 F8 隨後送一次，第三個被攔下。整套播放測試 285 通過、3 略過。產品候選 f533e1db，含額外回歸測試的本機 head 為 1af5815b。實機版 '+sha+' 含 I24 與時間戳探針。[舊版失敗](overnight-evidence/stop-ordinal-red.log) · [本機測試](overnight-evidence/stop-ordinal-batch-green.log)','',
'Model 12 韌體 1.50 0103、UM‑ONE、48 kHz／256 取樣、120 BPM。每輪送 576 個 F8，Stop 提前量以原本下一個 F8 的排定時間為零。補償設定逐次由 API 讀回。末 F8 的交付時間以程式辨認輸入 FC 為零，負值表示在 FC 前已呼叫原生輸出。','',
'| Beat Clock 補償 | Stop 提前 | 輸入／輸出 F8 | 本輪攔下 | 最後 F8 交付 | 穩態 F8 間距中位數 |',
'|---|---:|---:|---:|---:|---:|']
for r in rows:
    lines.append(f"| {'開' if r['mode']=='on' else '關'} | {r['advance_ms']} ms | {r['input']}／{r['output']} | {len(r['suppressions'])} | {r['last_send_begin_ms']:+.3f} ms | {r['steady_median_spacing_ms']:.3f} ms |")
equal=sum(r['output']==r['input'] for r in rows)
lost=sum(r['omitted'] for r in rows)
extra=sum(r['surplus'] for r in rows)
pre=sum(r['surplus'] for r in rows if r['last_send_end_ms']<0)
post=sum(r['returned_after_output_stop'] for r in rows)
lines+=['',f'八輪中 {equal} 輪輸入、輸出數相符，總數短少 {lost} 個，多出 {extra} 個。多出的脈衝中有 {pre} 個在程式辨認輸入 FC 前已完成原生送出。輸出埠自身的 FC 後收到 {post} 個 F8。以上為實體收發計數；只有攔截探針有記錄的輪次能直接歸功於候選。短測不取代原始兩小時 H-10。[逐輪原始索引與交付時間](overnight-evidence/stop-ordinal-matrix-'+sha+'.json)','']
p=here.parent/'H10-時鐘速差與起停邊界.zh-TW.md'
assert heading not in p.read_text(encoding='utf-8-sig')
with p.open('a',encoding='utf-8') as f:
    f.write('\n'+'\n'.join(lines)+'\n')

